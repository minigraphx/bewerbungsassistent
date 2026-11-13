"""Drafts grouped the way a person thinks of their documents (#120).

Entwürfe und Versionen shows the CV, one letter per application, style and building blocks, and the search
profile; each document lists its versions newest first. Job ads (`bewerbungen/<id>/stelle.md`) are copies of
the posting, not the person's own writing, so the page leaves them out. A version that went out with an application
names its company and date (#240), so the page can show only the documents used.
"""
import pathlib

import inhalte
from unterlagen import OWN_CV, OWN_LETTER

GROUPS = (("lebenslauf", "Lebenslauf"), ("anschreiben", "Anschreiben"), ("stil", "Stil und Bausteine"),
          ("suchprofil", "Suchprofil"), ("weitere", "Weitere"))
JOB_AD = "stelle.md"
LETTERS = {"anschreiben.yaml": "Anschreiben", OWN_LETTER: "Eigenes Anschreiben"}
TITLES = {"anschreiben/stil.md": "Stilprofil", "anschreiben/bausteine.md": "Textbausteine",
          OWN_CV: "Eigener Lebenslauf (PDF)"}
CV_FILES = ("cv.yaml", "varianten.yaml", OWN_CV)  # OWN_CV: uploaded on the page Lebenslauf und Dateien


def _parts(rel: str) -> tuple[str, ...]:
    return pathlib.PurePosixPath(rel).parts


def is_job_ad(rel: str) -> bool:
    parts = _parts(rel)
    return len(parts) == 3 and parts[0] == "bewerbungen" and parts[2] == JOB_AD


def _is_letter(rel: str) -> bool:
    parts = _parts(rel)
    return len(parts) == 3 and parts[0] == "bewerbungen" and parts[2] in LETTERS


def category(rel: str) -> str:
    parts = _parts(rel)
    if rel in CV_FILES or parts[0] == "jobs":
        return "lebenslauf"
    if _is_letter(rel):
        return "anschreiben"
    if parts[0] == "anschreiben":
        return "stil"
    if rel == "suchprofil.md":
        return "suchprofil"
    return "weitere"


def document_title(rel: str, companies: dict[str, str]) -> str:
    """Name of the document on the page; a letter carries its company, or its folder once the entry is gone."""
    if _is_letter(rel):
        _, entry_id, name = _parts(rel)
        return f"{LETTERS[name]} {companies.get(entry_id) or entry_id}"
    if rel in TITLES:
        return TITLES[rel]
    return inhalte.titel(rel)


def sent_with(draft: dict, sendings: dict[str, dict]) -> list[dict]:
    """The applications a version went out with; one whose entry is gone keeps the purpose it was recorded with."""
    return [{**sendings[p]} if p in sendings else {"firma": None, "datum": None, "zweck": p}
            for p in draft.get("genutzt_fuer", ())]


def _documents(drafts: list[dict], companies: dict[str, str], sendings: dict[str, dict]) -> dict[str, list[dict]]:
    """Documents per category, in the order of their newest version; `drafts` come newest first."""
    by_file: dict[str, list[dict]] = {}
    for draft in drafts:
        by_file.setdefault(draft["datei"], []).append(draft)
    documents: dict[str, list[dict]] = {}
    for rel, versions in by_file.items():
        title = document_title(rel, companies)
        shown = [{**v, "titel": title, "versendet": sent_with(v, sendings)} for v in versions]
        document = {"datei": rel, "titel": title, "fassungen": shown,
                    "verwendet": any(v["versendet"] for v in shown)}
        documents.setdefault(category(rel), []).append(document)
    return documents


def group(drafts: list[dict], companies: dict[str, str], sendings: dict[str, dict]) -> list[dict]:
    """Groups in a fixed order, empty ones left out; job ads never appear. `sendings` from `versand.sendings`."""
    documents = _documents([d for d in drafts if not is_job_ad(d["datei"])], companies, sendings)
    return [{"art": art, "titel": title, "dokumente": documents[art]} for art, title in GROUPS if art in documents]
