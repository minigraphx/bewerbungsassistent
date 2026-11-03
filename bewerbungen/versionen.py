"""Optional extra copy of sent versions in Git (MIN-303, MIN-304).

The own storage is complete without Git: sent PDFs stay under `versendet/`, the data they were built from
as used drafts (not deletable, see ablage.py), and the register says what went where. If Git is installed,
each Versand is also committed to the local Git of the data folder; nothing is ever pushed. Sent files from
times without Git are committed with the next Versand that has Git.
"""
import pathlib
import shutil
import subprocess
from typing import Protocol

from dateien import relativ

ERSATZ_AUTOR = "Bewerbungsassistent"
ERSATZ_MAIL = "bewerbungsassistent@localhost"


class Versionierung(Protocol):
    hinweis: str

    def friere_ein(self, pfade: list[pathlib.Path], nachricht: str) -> str | None: ...

    def verlauf(self, anzahl: int = 50) -> list[dict]: ...


class GitVersionen:
    hinweis = ("Versendete Fassungen sind gesichert: die PDFs unter versendet/, die Daten als genutzte Entwürfe. "
               "Zusätzlich hält das lokale Git des Datenordners jeden Versand fest (kein automatischer Push).")

    def __init__(self, ordner: pathlib.Path) -> None:
        self.ordner = ordner.resolve()

    def _git(self, *args: str, pruefen: bool = True) -> subprocess.CompletedProcess:
        # --literal-pathspecs: Dateinamen nie als Muster deuten
        ergebnis = subprocess.run(["git", "--literal-pathspecs", "-C", str(self.ordner), *args], capture_output=True)
        if pruefen and ergebnis.returncode != 0:
            meldung = ergebnis.stderr.decode(errors="replace").strip()
            raise RuntimeError(f"git {args[0]} fehlgeschlagen: {meldung}")
        return ergebnis

    def _sicherstellen(self) -> None:
        if self._git("rev-parse", "--git-dir", pruefen=False).returncode != 0:
            self._git("init", "-q")

    def _autor(self) -> list[str]:
        name = self._git("config", "user.name", pruefen=False).stdout.strip()
        mail = self._git("config", "user.email", pruefen=False).stdout.strip()
        return [] if name and mail else ["-c", f"user.name={ERSATZ_AUTOR}", "-c", f"user.email={ERSATZ_MAIL}"]

    def friere_ein(self, pfade: list[pathlib.Path], nachricht: str) -> str | None:
        """Nur die angegebenen Dateien committen; andere Änderungen im Ordner bleiben unberührt."""
        rel = [relativ(p, self.ordner) for p in pfade]
        self._sicherstellen()
        self._git("add", "--", *rel)
        if self._git("diff", "--cached", "--quiet", "--", *rel, pruefen=False).returncode == 0:
            return None
        ergebnis = subprocess.run(
            ["git", "--literal-pathspecs", "-C", str(self.ordner), *self._autor(), "commit", "-q", "-m", nachricht, "--", *rel],
            capture_output=True, text=True,
        )
        if ergebnis.returncode != 0:
            raise RuntimeError(f"Git-Commit fehlgeschlagen: {ergebnis.stderr.strip()}")
        return self._git("rev-parse", "HEAD").stdout.decode().strip()

    def verlauf(self, anzahl: int = 50) -> list[dict]:
        if self._git("rev-parse", "HEAD", pruefen=False).returncode != 0:
            return []
        trenner = "\x1f"
        roh = self._git("log", f"-{anzahl}", f"--format=%x1e%H{trenner}%aI{trenner}%s", "--name-only").stdout.decode()
        eintraege = []
        for block in filter(None, roh.split("\x1e")):
            kopf, *dateien = block.strip().splitlines()
            commit, datum, nachricht = kopf.split(trenner, 2)
            eintraege.append({"commit": commit, "datum": datum, "nachricht": nachricht, "dateien": [d for d in dateien if d]})
        return eintraege

    def inhalt(self, commit: str, rel: str) -> bytes:
        if not all(c in "0123456789abcdef" for c in commit) or len(commit) < 7:
            raise ValueError("Ungültige Commit-ID")
        relativ(self.ordner / rel, self.ordner)
        return self._git("show", f"{commit}:{rel}").stdout


class OhneGit:
    hinweis = "Versendete Fassungen sind gesichert: die PDFs unter versendet/, die Daten als genutzte Entwürfe."

    def __init__(self, ordner: pathlib.Path) -> None:
        self.ordner = ordner.resolve()

    def friere_ein(self, pfade: list[pathlib.Path], nachricht: str) -> str | None:
        for p in pfade:
            relativ(p, self.ordner)
        return None

    def verlauf(self, anzahl: int = 50) -> list[dict]:
        return []


def waehle(ordner: pathlib.Path) -> Versionierung:
    return GitVersionen(ordner) if shutil.which("git") else OhneGit(ordner)
