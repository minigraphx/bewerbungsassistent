"""Entwürfe (MIN-303): Jedes Speichern legt einen Entwurf mit Datum an.

Entwürfe liegen im Datenordner unter `.entwuerfe/` (nicht in Git): Inhalte nach SHA-256 in `objekte/`,
jeder Inhalt nur einmal, dazu `index.yaml` mit Datei, Zeit und Beschreibung. Entwürfe sind löschbar,
solange sie nicht genutzt wurden; genutzt heisst versendet (MIN-263), dann friert `versionen.py` den
Stand in Git ein.
"""
import dataclasses
import datetime
import difflib
import hashlib
import pathlib
import threading

from dateien import im_ordner, lies_yaml, relativ, schreibe_atomar, schreibe_yaml, sichere_gitignore

ORDNER = ".entwuerfe"


@dataclasses.dataclass(frozen=True)
class Entwurf:
    id: str
    datei: str  # relativ zum Datenordner
    hash: str
    zeit: str  # ISO 8601
    beschreibung: str
    genutzt_fuer: tuple[str, ...] = ()

    @property
    def genutzt(self) -> bool:
        return bool(self.genutzt_fuer)

    def als_dict(self) -> dict:
        return {**dataclasses.asdict(self), "genutzt_fuer": list(self.genutzt_fuer), "genutzt": self.genutzt}


def _aus_dict(d: dict) -> Entwurf:
    return Entwurf(
        id=d["id"], datei=d["datei"], hash=d["hash"], zeit=d["zeit"],
        beschreibung=d.get("beschreibung", ""), genutzt_fuer=tuple(d.get("genutzt_fuer", ())),
    )


class Ablage:
    def __init__(self, datenordner: pathlib.Path) -> None:
        self.ordner = datenordner.resolve()
        self._basis = self.ordner / ORDNER
        self._objekte = self._basis / "objekte"
        self._index = self._basis / "index.yaml"
        self._sperre = threading.Lock()

    def sichere_gitignore(self) -> None:
        sichere_gitignore(self.ordner, [f"{ORDNER}/"])

    # Lesen

    def _eintraege(self) -> list[Entwurf]:
        return [_aus_dict(d) for d in lies_yaml(self._index, [])]

    def _schreibe(self, eintraege: list[Entwurf]) -> None:
        daten = [{k: v for k, v in e.als_dict().items() if k != "genutzt"} for e in eintraege]
        schreibe_yaml(self._index, daten, "# Entwürfe, geschrieben vom Bewerbungsassistenten\n")

    def liste(self, datei: pathlib.Path | None = None) -> list[Entwurf]:
        """Entwürfe, neueste zuerst; optional nur die einer Datei."""
        rel = relativ(datei, self.ordner) if datei is not None else None
        alle = [e for e in self._eintraege() if rel is None or e.datei == rel]
        return sorted(alle, key=lambda e: e.zeit, reverse=True)

    def hole(self, entwurf_id: str) -> Entwurf:
        for e in self._eintraege():
            if e.id == entwurf_id:
                return e
        raise KeyError(f"Entwurf {entwurf_id!r} nicht gefunden")

    def inhalt(self, entwurf_id: str) -> bytes:
        return (self._objekte / self.hole(entwurf_id).hash).read_bytes()

    # Schreiben

    def speichere(self, pfad: pathlib.Path, beschreibung: str) -> Entwurf | None:
        """Aktuellen Inhalt der Datei als Entwurf ablegen; None, wenn er dem letzten Entwurf gleicht."""
        with self._sperre:
            return self._speichere(pfad, beschreibung)

    def _speichere(self, pfad: pathlib.Path, beschreibung: str) -> Entwurf | None:
        rel = relativ(pfad, self.ordner)
        inhalt = pfad.read_bytes()
        digest = hashlib.sha256(inhalt).hexdigest()
        eintraege = self._eintraege()
        letzte = sorted((e for e in eintraege if e.datei == rel), key=lambda e: e.zeit)
        if letzte and letzte[-1].hash == digest:
            return None
        objekt = self._objekte / digest
        if not objekt.exists():
            schreibe_atomar(objekt, inhalt)
        jetzt = datetime.datetime.now()
        entwurf = Entwurf(
            id=f"{jetzt:%Y%m%d-%H%M%S-%f}-{digest[:8]}", datei=rel, hash=digest,
            zeit=jetzt.isoformat(timespec="microseconds"), beschreibung=beschreibung,
        )
        self._schreibe(eintraege + [entwurf])
        return entwurf

    def stelle_her(self, entwurf_id: str) -> Entwurf:
        """Datei auf den Entwurf zurücksetzen; der Stand davor wird vorher als Entwurf gesichert."""
        with self._sperre:
            entwurf = self.hole(entwurf_id)
            ziel = im_ordner(self.ordner, entwurf.datei)
            if ziel.exists():
                self._speichere(ziel, "Stand vor dem Wiederherstellen")
            schreibe_atomar(ziel, (self._objekte / entwurf.hash).read_bytes())
            self._speichere(ziel, f"Wiederhergestellt: {entwurf.beschreibung}")
            return entwurf

    def loesche(self, entwurf_id: str) -> None:
        with self._sperre:
            entwurf = self.hole(entwurf_id)
            if entwurf.genutzt:
                raise ValueError(f"Entwurf ist genutzt ({', '.join(entwurf.genutzt_fuer)}) und kann nicht gelöscht werden")
            rest = [e for e in self._eintraege() if e.id != entwurf_id]
            self._schreibe(rest)
            if not any(e.hash == entwurf.hash for e in rest):
                (self._objekte / entwurf.hash).unlink(missing_ok=True)

    def markiere_genutzt(self, pfade: list[pathlib.Path], zweck: str) -> list[Entwurf]:
        """Aktuellen Stand der Dateien als genutzt markieren (legt fehlende Entwürfe an)."""
        with self._sperre:
            for pfad in pfade:
                self._speichere(pfad, "Stand beim Versand")
            hashes = {relativ(p, self.ordner): hashlib.sha256(p.read_bytes()).hexdigest() for p in pfade}
            neu = [
                dataclasses.replace(e, genutzt_fuer=e.genutzt_fuer + (zweck,))
                if hashes.get(e.datei) == e.hash and zweck not in e.genutzt_fuer else e
                for e in self._eintraege()
            ]
            self._schreibe(neu)
            return [e for e in neu if hashes.get(e.datei) == e.hash]

    # Vergleich

    def vergleiche(self, id_a: str, id_b: str) -> str:
        a, b = self.hole(id_a), self.hole(id_b)
        binaer = "Inhalt ist binär (z.B. PDF) und lässt sich nicht als Text vergleichen."
        roh_a, roh_b = self.inhalt(id_a), self.inhalt(id_b)
        if b"\x00" in roh_a or b"\x00" in roh_b:
            return binaer
        try:
            text_a, text_b = roh_a.decode("utf-8"), roh_b.decode("utf-8")
        except UnicodeDecodeError:
            return binaer
        return "".join(difflib.unified_diff(
            text_a.splitlines(keepends=True), text_b.splitlines(keepends=True),
            fromfile=f"{a.datei} ({a.zeit[:16]})", tofile=f"{b.datei} ({b.zeit[:16]})",
        ))
