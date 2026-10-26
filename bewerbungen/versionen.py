"""Genutzte Fassungen einfrieren (MIN-303): Beim Versand werden PDFs und Daten im lokalen Git des
Datenordners committet. Gepusht wird nie automatisch.

Ohne installiertes Git (MIN-304) bleiben die versendeten Dateien trotzdem unter `versendet/` und im
Register erhalten; sie werden beim ersten Versand mit Git mit eingefroren, es geht also nichts verloren.
"""
import pathlib
import shutil
import subprocess
from typing import Protocol

from dateien import relativ

ERSATZ_AUTOR = "Bewerbungsassistent"
ERSATZ_MAIL = "bewerbungsassistent@localhost"
INSTALLATION = "macOS: xcode-select --install · Windows/Linux: https://git-scm.com/downloads"


class Versionierung(Protocol):
    hinweis: str

    def friere_ein(self, pfade: list[pathlib.Path], nachricht: str) -> str | None: ...

    def verlauf(self, anzahl: int = 50) -> list[dict]: ...


class GitVersionen:
    hinweis = "Versionen werden im lokalen Git des Datenordners festgehalten (kein automatischer Push)."

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
    hinweis = (
        "Git ist nicht installiert: Versendete Fassungen bleiben unter versendet/ und im Register erhalten, "
        f"werden aber noch nicht eingefroren. Git installieren ({INSTALLATION}); beim nächsten Versand wird "
        "alles nachgeholt."
    )

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
