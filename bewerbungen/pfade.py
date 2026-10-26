"""Macht das Nachbarmodul `lebenslauf/` importierbar (build, anschreiben, fotoausschnitt).

Die Module des Bewerbungsassistenten liegen als Ordner nebeneinander; `bewerbungen` baut auf `lebenslauf`
auf, nie umgekehrt.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
LEBENSLAUF = ROOT.parent / "lebenslauf"

if str(LEBENSLAUF) not in sys.path:
    sys.path.insert(0, str(LEBENSLAUF))
