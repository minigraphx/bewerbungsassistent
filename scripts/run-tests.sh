#!/bin/sh
# Runs the named test files the way scripts/gate.sh runs their module, for
# `pullboard test` (pullboard.json affectedTests). Paths are from the repo root,
# e.g. ./desktop/tests/test_updates.py ./bewerbungen/tests/texte.test.cjs.
# Prints TAP with one line per file; exit 0 only when every file passed.
set -u

root=$(cd "$(dirname "$0")/.." && pwd) || exit 1
cd "$root" || exit 1

# Tests must never reach the real keychain.
export PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring

work=$(mktemp -d) || exit 1
trap 'rm -rf "$work"' EXIT

# The venv lives only in the main checkout. A worktree reaches it through the
# git common dir; Pullboard's snapshot is a `git clone --shared` in a temp
# folder, which reaches it only through the alternates file of its objects.
find_python() {
  common=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null) || return 1
  candidate="$(dirname "$common")/.venv/bin/python"
  if [ -x "$candidate" ]; then echo "$candidate"; return 0; fi
  alternates="$common/objects/info/alternates"
  [ -f "$alternates" ] || return 1
  while IFS= read -r objects; do
    candidate="$(dirname "$(dirname "$objects")")/.venv/bin/python"
    if [ -x "$candidate" ]; then echo "$candidate"; return 0; fi
  done <"$alternates"
  return 1
}

# Sets group, folder and target for a path, or returns 1 for an unknown kind.
# Each group mirrors one run line of scripts/gate.sh.
classify() {
  case $1 in
    *..*) return 1 ;;
    bewerbungen/tests/*.test.cjs | onboarding/tests/*.test.cjs)
      folder=${1%%/*}; group="node-$folder"; target=${1#*/} ;;
    erweiterung/tests/*.test.mjs)
      folder=.; group=node-erweiterung; target=$1 ;;
    docs/webseite/tests/test_*.py)
      folder=docs/webseite; group=py-webseite; target=${1#docs/webseite/} ;;
    bewerbungen/tests/test_*.py | desktop/tests/test_*.py | lebenslauf/tests/test_*.py | \
    onboarding/tests/test_*.py | vermittlung/tests/test_*.py)
      folder=${1%%/*}; group="py-$folder"; target=${1#*/} ;;
    *) return 1 ;;
  esac
}

# Runs one file and records its exit status, log and duration under its index.
run_file() { # index
  read -r folder <"$work/$1.folder"
  read -r target <"$work/$1.target"
  read -r group <"$work/$1.group"
  started=$(date +%s)
  case $group in
    py-*) ( cd "$root/$folder" && "$python" -m pytest "$target" -q ) ;;
    node-*) ( cd "$root/$folder" && node --test "$target" ) ;;
  esac >"$work/$1.log" 2>&1
  echo $? >"$work/$1.status"
  echo $(( $(date +%s) - started )) >"$work/$1.seconds"
}

fail_early() { # index message
  echo "$2" >"$work/$1.log"
  echo 1 >"$work/$1.status"
  echo 0 >"$work/$1.seconds"
}

count=0
needs_python=0
for arg in "$@"; do
  count=$((count + 1))
  path=${arg#./}
  echo "$arg" >"$work/$count.arg"
  if ! classify "$path"; then
    fail_early "$count" "unknown kind of test file: $arg"
  elif [ ! -f "$root/$path" ]; then
    fail_early "$count" "no such file: $arg"
  else
    echo "$folder" >"$work/$count.folder"
    echo "$target" >"$work/$count.target"
    echo "$group" >"$work/$count.group"
    echo "$count" >>"$work/list.$group"
    case $group in py-*) needs_python=1 ;; esac
  fi
done

python=
if [ "$needs_python" = 1 ] && ! python=$(find_python); then
  echo "run-tests: no .venv/bin/python in the main checkout; create the venv there" >&2
  for list in "$work"/list.py-*; do
    while read -r index; do fail_early "$index" "no .venv/bin/python in the main checkout"; done <"$list"
    rm -f "$list"
  done
fi

# Modules run in parallel like the gate; files of one module run one after the
# other, since they may share fixtures such as ports or temp folders.
for list in "$work"/list.*; do
  [ -f "$list" ] || continue
  ( while read -r index; do run_file "$index"; done <"$list" ) &
done
wait

echo "TAP version 13"
failed=0
index=0
while [ "$index" -lt "$count" ]; do
  index=$((index + 1))
  read -r arg <"$work/$index.arg"
  read -r status <"$work/$index.status"
  if [ "$status" = 0 ]; then
    echo "ok $index - $arg"
    continue
  fi
  failed=1
  read -r seconds <"$work/$index.seconds"
  # The YAML block lets Pullboard attribute the failure to this file.
  echo "not ok $index - $arg"
  echo "  ---"
  echo "  duration_ms: $((seconds * 1000))"
  echo "  location: '$arg:1:1'"
  echo "  exitCode: $status"
  echo "  ..."
  # Prefixed so the inner runner's own TAP lines cannot be read as ours.
  tail -80 "$work/$index.log" | sed 's/^/# /'
done
echo "1..$count"

if [ "$count" = 0 ]; then
  echo "run-tests: name the test files to run" >&2
  exit 1
fi
exit "$failed"
