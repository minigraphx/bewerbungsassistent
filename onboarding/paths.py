"""Makes the neighbouring modules `bewerbungen/` (drafts, file helpers) and `lebenslauf/` importable.

`onboarding` builds on both, never the other way round.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
for module in ("bewerbungen", "lebenslauf"):
    folder = str(ROOT.parent / module)
    if folder not in sys.path:
        sys.path.insert(0, folder)
