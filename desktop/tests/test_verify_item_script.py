"""scripts/verify-item.sh lets its verifier break a check in its own worktree, and nothing else (#452, PB4).

The script runs here in a throwaway git repository with a stub `claude` on PATH that only records its
arguments, so no Claude session ever starts. A small matcher then reads the recorded rules the way the
Claude Code permission docs describe them: a deny rule wins; the Edit and Write tools both match Edit
rules; a path rule anchors at the filesystem root with `//`, at the primary working directory with `/`,
and at the current directory otherwise; a Bash rule matches its text as written, `*` standing for any
run of characters, and every part of a compound command needs its own rule unless it is read-only.
"""
import json
import os
import pathlib
import re
import subprocess

import pytest

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
SCRIPT = REPO / "scripts" / "verify-item.sh"
# The verifier also inherits the allow rules of the project settings and of the developer's own settings,
# where merging a pull request is commonly allowed; only the script's deny rules can hold those back.
INHERITED = tuple(json.loads((REPO / ".claude" / "settings.json").read_text(encoding="utf-8"))
                  .get("permissions", {}).get("allow", [])) + ("Bash(gh pr merge *)",)
STUB = '#!/bin/sh\nprintf "%s\\0" "$@" > "$CLAUDE_ARGS"\n'
READ_ONLY = {"cd", "cat", "ls", "grep", "head", "tail", "echo", "pwd", "wc"}
OPERATORS = re.compile(r"\s*(?:&&|\|\||;|\|)\s*")
REDIRECT = re.compile(r"\s*\d?>&\d")
NULL_KEYRING = "PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring"


class Run:
    """What one stubbed run of the script handed to `claude`."""

    def __init__(self, args: list[str], main: pathlib.Path):
        self.main = str(main)
        self.prompt = args[args.index("-p") + 1]
        self.allowed = flag_values(args, "--allowedTools")
        self.disallowed = flag_values(args, "--disallowedTools")
        seat = re.search(r"\.claude/worktrees/(verify-\d+)", self.prompt)
        assert seat, "the prompt names no verify worktree"
        self.worktree = f"{self.main}/.claude/worktrees/{seat.group(1)}"


def flag_values(args: list[str], flag: str) -> list[str]:
    start = args.index(flag) + 1
    end = next((i for i in range(start, len(args)) if args[i].startswith("--")), len(args))
    return args[start:end]


@pytest.fixture(scope="module")
def run(tmp_path_factory) -> Run:
    base = tmp_path_factory.mktemp("verify-item")
    main = base / "repo"
    main.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=main, check=True)
    bin_dir = base / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "claude"
    stub.write_text(STUB, encoding="utf-8")
    stub.chmod(0o755)
    record = base / "args"
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}", "CLAUDE_ARGS": str(record)}
    subprocess.run(["sh", str(SCRIPT), "claude-test-model"], cwd=main, env=env, check=True,
                   stdin=subprocess.DEVNULL, capture_output=True)
    args = record.read_bytes().decode("utf-8").split("\0")[:-1]
    common = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=main,
                            check=True, capture_output=True, text=True).stdout.strip()
    return Run(args, pathlib.Path(common).parent)


def glob_regex(pattern: str) -> re.Pattern:
    parts = re.split(r"(\*\*/?|\*)", pattern)
    wildcards = {"**/": "(?:.*/)?", "**": ".*", "*": "[^/]*"}
    return re.compile("".join(wildcards.get(part, re.escape(part)) for part in parts))


def anchored(rule_path: str, main: str, cwd: str) -> str:
    if rule_path.startswith("//"):
        return rule_path[1:]
    if rule_path.startswith("~/"):
        return str(pathlib.Path.home()) + rule_path[1:]
    if rule_path.startswith("/"):
        return main + rule_path
    return f"{cwd}/{rule_path.removeprefix('./')}"


def edit_rule_matches(rule: str, path: str, main: str, cwd: str) -> bool:
    if rule == "Edit":
        return True
    found = re.fullmatch(r"Edit\((.+)\)", rule)
    return bool(found) and bool(glob_regex(anchored(found.group(1), main, cwd)).fullmatch(path))


def may_edit(run: Run, path: str, cwd: str) -> bool:
    """Whether the Edit or Write tool may change `path` without a prompt; both match Edit rules."""
    if any(edit_rule_matches(rule, path, run.main, cwd) for rule in run.disallowed):
        return False
    return any(edit_rule_matches(rule, path, run.main, cwd) for rule in run.allowed)


def bash_rule_matches(rule: str, command: str) -> bool:
    found = re.fullmatch(r"Bash\((.+)\)", rule)
    if not found:
        return rule == "Bash"
    text = found.group(1)
    # A trailing " *" also matches the bare command.
    forms = (text, text[:-2]) if text.endswith(" *") else (text,)
    return any(re.fullmatch(".*".join(re.escape(part) for part in form.split("*")), command) for form in forms)


def may_run(run: Run, command: str) -> bool:
    """Whether a Bash command runs without a prompt: each part allowed or read-only, and no part denied."""
    parts = [REDIRECT.sub("", part).strip() for part in OPERATORS.split(command)]
    for part in parts:
        if any(bash_rule_matches(rule, part) for rule in run.disallowed):
            return False
        allowed = (*run.allowed, *INHERITED)
        if part.split()[0] not in READ_ONLY and not any(bash_rule_matches(rule, part) for rule in allowed):
            return False
    return True


def broken_file(run: Run) -> str:
    return f"{run.worktree}/bewerbungen/sprachen/bewerbung.json"


@pytest.mark.parametrize("subfolder", ["", "/bewerbungen"])
def test_verifier_may_edit_its_own_worktree_after_cd(run, subfolder):
    assert may_edit(run, broken_file(run), cwd=run.worktree + subfolder)


def test_verifier_may_edit_its_own_worktree_from_the_main_checkout(run):
    assert may_edit(run, broken_file(run), cwd=run.main)


@pytest.mark.parametrize("where", [
    "bewerbungen/sprachen/bewerbung.json",
    ".claude/settings.json",
    ".claude/worktrees/app-6/bewerbungen/sprachen/bewerbung.json",
    ".claude/worktrees/verify-1/bewerbungen/sprachen/bewerbung.json",
])
def test_verifier_may_not_edit_the_main_checkout_or_other_worktrees(run, where):
    path = f"{run.main}/{where}"
    for cwd in (run.main, run.worktree, f"{run.worktree}/bewerbungen"):
        assert not may_edit(run, path, cwd), f"{path} is editable from {cwd}"


def test_a_worktree_whose_name_starts_with_the_seat_is_not_editable(run):
    assert not may_edit(run, f"{run.worktree}0/bewerbungen/app.py", cwd=run.worktree)


def test_every_edit_rule_is_absolute_and_inside_the_verify_worktree(run):
    tool_names = {"Edit", "Write", "NotebookEdit", "MultiEdit"}
    edit_rules = [rule for rule in run.allowed if rule.split("(")[0] in tool_names]
    assert edit_rules == [f"Edit(/{run.worktree}/**)"]


@pytest.mark.parametrize("command", [
    "{main}/.venv/bin/python -m sprachen_pruefen",
    "{main}/.venv/bin/python -m sprachen_pruefen --alle 2>&1 | tail -8",
    NULL_KEYRING + " {main}/.venv/bin/python -m sprachen_pruefen",
    "cd {worktree}/bewerbungen",
    "pullboard test ./bewerbungen/tests/test_sprachen.py",
    "git checkout -- bewerbungen/sprachen/bewerbung.json",
])
def test_verifier_may_run_the_scanner_tests_and_restore(run, command):
    assert may_run(run, command.format(main=run.main, worktree=run.worktree))


def test_the_scanner_rule_does_not_cover_other_programs(run):
    assert not may_run(run, f"rm -rf {run.main} {run.main}/.venv/bin/python -m sprachen_pruefen")


@pytest.mark.parametrize("command", [
    "git push", "git push origin HEAD:main", "pullboard merged 452 abc1234", "pullboard land 452",
    "pullboard submit 452", "gh pr merge 377 --squash", "git merge main",
])
def test_merging_pushing_and_submitting_stay_refused(run, command):
    assert not may_run(run, command)


@pytest.mark.parametrize("command", ["git stash", "git stash push -u -m verify", "git stash pop"])
def test_git_stash_is_refused(run, command):
    assert not any(rule.startswith("Bash(git stash") for rule in run.allowed)
    assert not may_run(run, command)


def test_prompt_names_the_scanner_command_and_the_restore(run):
    assert f"{run.main}/.venv/bin/python -m sprachen_pruefen" in run.prompt
    assert "git checkout --" in run.prompt
    assert "git stash" not in run.prompt
