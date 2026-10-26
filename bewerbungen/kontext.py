"""Gemeinsamer Zustand der lokalen Oberfläche: Datenordner, Build-Ordner, Ablage der Entwürfe, Versionierung."""
import dataclasses
import datetime
import pathlib
import threading
from typing import Callable, TypeVar

from ablage import Ablage
from register import Register
from varianten import Varianten
from versionen import Versionierung

T = TypeVar("T")


@dataclasses.dataclass(frozen=True)
class Kontext:
    daten: pathlib.Path
    build: pathlib.Path
    ablage: Ablage
    versionierung: Versionierung
    heute: Callable[[], datetime.date] = datetime.date.today
    sperre: threading.Lock = dataclasses.field(default_factory=threading.Lock)
    cache: dict = dataclasses.field(default_factory=dict)  # z.B. die Foto-Vorschau (teurer Typst-Compiler)

    def register(self) -> Register:
        return Register(self.daten)

    def varianten(self) -> Varianten:
        return Varianten(self.daten)

    def mit_entwurf(self, pfad: pathlib.Path, beschreibung: str, schreiben: Callable[[], T]) -> T:
        """Datei ändern und dabei Entwürfe anlegen: vom Stand davor (falls noch nicht gesichert) und vom neuen."""
        with self.sperre:
            if pfad.is_file():
                self.ablage.speichere(pfad, f"Stand vor: {beschreibung}")
            ergebnis = schreiben()
            if pfad.is_file():
                self.ablage.speichere(pfad, beschreibung)
            return ergebnis
