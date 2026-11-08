"""A line diff a person can read before a file is replaced (G26).

The standard library's difflib does the matching, so no new dependency comes in. Unchanged stretches shrink to a
few lines of context around each change; a gap marks what is left out. Kinds: gleich, weg, neu, luecke.
"""
import difflib

CONTEXT_LINES = 2
SAME, REMOVED, ADDED, GAP = "gleich", "weg", "neu", "luecke"


def line_diff(old: str, new: str) -> list[dict[str, str]]:
    """The lines that differ between old and new, with context; empty when nothing differs."""
    before, after = old.splitlines(), new.splitlines()
    if before == after:
        return []
    matcher = difflib.SequenceMatcher(a=before, b=after, autojunk=False)
    groups = list(matcher.get_grouped_opcodes(CONTEXT_LINES))
    lines: list[dict[str, str]] = []
    for number, group in enumerate(groups):
        if number or group[0][1] > 0:
            lines.append({"art": GAP, "text": ""})
        for tag, i1, i2, j1, j2 in group:
            if tag == "equal":
                lines.extend({"art": SAME, "text": t} for t in before[i1:i2])
                continue
            lines.extend({"art": REMOVED, "text": t} for t in before[i1:i2])
            lines.extend({"art": ADDED, "text": t} for t in after[j1:j2])
    if groups[-1][-1][2] < len(before):
        lines.append({"art": GAP, "text": ""})
    return lines
