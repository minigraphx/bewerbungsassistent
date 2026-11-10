"""Drafts grouped the way a person thinks of their documents (#120).

Entwürfe und Versionen shows the CV, one letter per application, style and building blocks, and the search
profile; each document lists its versions newest first. Job ads (`bewerbungen/<id>/stelle.md`) are copies of
the posting, not the person's own writing, so the page leaves them out.
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
CV_FILES = ("cv.yaml", "varianten.yaml", OWN_CV)  # OWN_CV: uploaded on the page Meine Dateien


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


def _documents(drafts: list[dict], companies: dict[str, str]) -> dict[str, list[dict]]:
    """Documents per category, in the order of their newest version; `drafts` come newest first."""
    by_file: dict[str, list[dict]] = {}
    for draft in drafts:
        by_file.setdefault(draft["datei"], []).append(draft)
    documents: dict[str, list[dict]] = {}
    for rel, versions in by_file.items():
        title = document_title(rel, companies)
        document = {"datei": rel, "titel": title, "fassungen": [{**v, "titel": title} for v in versions]}
        documents.setdefault(category(rel), []).append(document)
    return documents


def group(drafts: list[dict], companies: dict[str, str]) -> list[dict]:
    """Groups in a fixed order, empty ones left out; job ads never appear."""
    documents = _documents([d for d in drafts if not is_job_ad(d["datei"])], companies)
    return [{"art": art, "titel": title, "dokumente": documents[art]} for art, title in GROUPS if art in documents]
