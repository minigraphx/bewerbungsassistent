"""Rules for documents uploaded in the onboarding template (old CV, references, certificates, letters).

The rules live in form.json ("documents") and are the same in `src/documents.js`; both run the shared
cases in `tests/cases.json` ("documentCases"). An entry is {"category", "name", "size"}; the name is
only a file name (no folders), the category is one of the folders under `dokumente/` in the data folder.
"""
import re

from validation import ValidationError, for_track

CATEGORY_ID = re.compile(r"[a-z0-9-]+")
BYTES_PER_MB = 1_000_000
MESSAGES = {
    "type": "Unerwarteter Eintrag.",
    "category": "Unbekannte Art von Unterlage.",
    "name": "Ungültiger Dateiname.",
    "extension": "Dieser Dateityp geht nicht. Erlaubt sind {allowed}.",
    "size": "Die Datei ist zu gross (höchstens {maxFileMB} MB).",
    "duplicate": "Diese Datei ist schon dabei.",
    "maxFiles": "Zu viele Dateien (höchstens {maxFiles}).",
    "total": "Zusammen sind die Dateien zu gross (höchstens {maxTotalMB} MB).",
}


def categories(form: dict) -> dict[str, dict]:
    return {c["id"]: c for c in form["documents"]["categories"]}


def extension(name: str) -> str:
    return name.rsplit(".", 1)[1].lower() if "." in name else ""


def allowed_extensions(form: dict, category: dict) -> list[str]:
    """File extensions a category accepts, from its file types (e.g. images only for certificates)."""
    types = form["documents"]["fileTypes"]
    return [ext for t in category["fileTypes"] for ext in types[t]["extensions"]]


def allowed_text(form: dict, category: dict) -> str:
    """German list of the accepted file types, e.g. „PDF, Word (.docx, .doc) und Textdateien (.txt)“."""
    types = form["documents"]["fileTypes"]
    labels = [label for t in category["fileTypes"] for label in types[t]["labels"]]
    return labels[0] if len(labels) == 1 else f"{', '.join(labels[:-1])} und {labels[-1]}"


def validate_documents(form: dict, entries) -> list[ValidationError]:
    if not isinstance(entries, list):
        return [ValidationError("documents", "type")]
    rules = form["documents"]
    known = categories(form)
    errors, seen, counts, total = [], set(), {}, 0
    for index, entry in enumerate(entries):
        code = _entry_error(form, known, entry, seen)
        if code:
            errors.append(ValidationError(f"documents.{index}", code))
        if isinstance(entry, dict) and isinstance(entry.get("category"), str) and entry["category"] in known:
            counts[entry["category"]] = counts.get(entry["category"], 0) + 1
        if isinstance(entry, dict) and _is_size(entry.get("size")):
            total += entry["size"]
    errors += [ValidationError(f"documents.{cid}", "maxFiles") for cid, count in counts.items()
               if count > known[cid]["maxFiles"]]
    if total > rules["maxTotalBytes"]:
        errors.append(ValidationError("documents", "total"))
    return errors


def _is_size(value) -> bool:
    return type(value) is int and value > 0


def _entry_error(form: dict, known: dict, entry, seen: set) -> str | None:
    rules = form["documents"]
    if not isinstance(entry, dict):
        return "type"
    category, name, size = entry.get("category"), entry.get("name"), entry.get("size")
    if not isinstance(category, str) or category not in known:
        return "category"
    if not isinstance(name, str) or not re.fullmatch(rules["namePattern"], name):
        return "name"
    if extension(name) not in allowed_extensions(form, known[category]):
        return "extension"
    if not _is_size(size) or size > rules["maxFileBytes"]:
        return "size"
    key = (category, name.lower())
    if key in seen:
        return "duplicate"
    seen.add(key)
    return None


def describe(form: dict, track: str, entries: list, error: ValidationError) -> str:
    """German message: category and file name, then what is wrong."""
    rules = form["documents"]
    known = categories(form)
    parts = error.path.split(".")
    params = {"maxFileMB": rules["maxFileBytes"] // BYTES_PER_MB, "maxTotalMB": rules["maxTotalBytes"] // BYTES_PER_MB,
              "maxFiles": "?", "allowed": "?"}
    where = ""
    if len(parts) == 2 and parts[1] in known:
        category = known[parts[1]]
        params["maxFiles"] = category["maxFiles"]
        where = for_track(category["title"], track)
    elif len(parts) == 2 and parts[1].isascii() and parts[1].isdigit() and int(parts[1]) < len(entries):
        entry = entries[int(parts[1])]
        if isinstance(entry, dict):
            category = known.get(entry.get("category")) if isinstance(entry.get("category"), str) else None
            if category:
                params["allowed"] = allowed_text(form, category)
            names = [for_track(category["title"], track) if category else "", entry.get("name")]
            where = ", ".join(str(n) for n in names if isinstance(n, str) and n)
    text = MESSAGES.get(error.code, error.code).format(**params)
    return f"{where}: {text}" if where else text
