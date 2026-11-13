"""Markdown basics from an onboarding bundle: search profile, style profile and building blocks.

Values are written as single lines (`inline`), so text from the bundle cannot open headings or
lists of its own. Section layout follows the templates in `vorlagen/`.
"""
import paths  # noqa: F401  (makes the module bewerbungen importable)
from search_plan import MODE_OFF, PORTALS
from values import highlight_texts, items, text

APPRENTICESHIP_SOURCES = [
    "Lehrstellennachweis LENA (berufsberatung.ch), yousty.ch, Lehrstellenseiten der Betriebe",
    "Die Browser-Erweiterung sucht auf LENA und yousty im Umkreis des Wohnorts; ohne Wohnort in den Kantonen",
]
JOB_OUTLINE = [
    "Einstieg: Bezug aufs Inserat und warum die Stelle interessiert.",
    "Passung: die wichtigsten Anforderungen mit Belegen.",
    "Aktuelle Stelle, soweit passend.",
    "Weitere Erfahrung, soweit passend.",
    "Lücken und Lernbereitschaft.",
    "Motivation für genau diese Firma.",
    "Schluss: Verfügbarkeit und Wunsch nach einem Gespräch.",
]
APPRENTICESHIP_OUTLINE = [
    "Einstieg: welcher Beruf und warum.",
    "Schnupperlehre oder Erfahrung, die zum Beruf passt.",
    "Stärken mit Beispiel.",
    "Warum genau dieser Betrieb.",
    "Schluss: Wunsch nach einer Schnupperlehre oder einem Gespräch.",
]
SALUTATION_FORMAL = "Sie-Form: „Sehr geehrte Frau <Nachname>“, ohne Namen „Guten Tag“."
SALUTATION_INFORMAL = "Du-Form, wenn das Inserat duzt: „Liebes <Firma>-Team“ / „Liebe <Vorname>“."
DEFAULT_GREETING = "Freundliche Grüsse"
GAPS_LATER = ("- Noch keine. Die App ergänzt sie nach und nach, wenn Inserate etwas verlangen, das fehlt; "
              "jede Lücke bestätigt die Person. Sie dienen dazu, die Passung von Stellen ehrlich zu bewerten.")
OWN_STATEMENT = "eigene Angabe"
RHYTHM = "Portale und Rhythmus"  # where the search reads its window and which portals are off (search_plan.py)
WINDOW_LABEL = "Zeitfenster"
WINDOW_LINE = "- Zeitfenster: {days} Tage"  # as the card on Suche einstellen writes it (routes_window.py)
PORTAL_HEAD = ("| Portal | Modus |", "|---|---|")
PORTAL_ROW = "| {portal} | {mode} |"
MODE_ON = "automatisch"


def inline(value) -> str:
    """One line of text: whitespace and line breaks collapse to single spaces."""
    return " ".join(text(value).split())


def search_profile(data: dict, track: str, note: str) -> str:
    parts = _search_apprenticeship(data) if track == "apprenticeship" else _search_job(data)
    title = "# Suchprofil Lehrstelle" if track == "apprenticeship" else "# Suchprofil"
    intro = f"{note}. Wird vom Skill `jobsuche` gelesen; ergänzen in der App oder von Hand."
    return _document(title, intro, parts)


def _search_job(data: dict) -> list[tuple[str, list[str]]]:
    person, search = data.get("person", {}), data.get("searchJob", {})
    directions = _numbered(search.get("directions"))
    exclusions = items(search.get("exclusions"))
    if exclusions:
        directions.append(f"- Ausschluss: {inline(_joined(exclusions))}")
    return [
        ("Person", _pairs(("Name", person.get("name")), ("Sprache der Antworten", "Deutsch"))),
        ("Suchrichtungen", directions),
        ("Region", _pairs(("Wohnort", search.get("home")), ("Pendelgrenze", search.get("commute")),
                          ("Kantone (job-room)", _joined(items(search.get("cantons")))), ("Remote", search.get("remote")))),
        ("Keywords", _pairs(("Kernliste", _joined(items(search.get("keywords")))))),
        ("Titelfilter", _pairs(("Positiv", _joined(items(search.get("titlePositive")))),
                               ("Ausschluss", _joined(items(search.get("titleExclude")))))),
        (RHYTHM, _rhythm(search)),
        ("Sprachen", _bullets([_joined(_languages(data))])),
        ("Abschluss und Erfahrung", _bullets([_education_summary(data)])),
        ("Stärken", _bullets([_joined(_strength_names(data))])),
        ("Typische Haken (offen benennen)", _gaps(data)),
        ("Rahmen", _pairs(("Frühester Start", search.get("start")), ("Pensum", search.get("workload")),
                          ("Befristung möglich", search.get("temporary")))),
        ("Zielfirmen mit Karriereseite", _bullets(items(search.get("targetCompanies")))),
    ]


def portal_row(portal: str, off: bool) -> str:
    return PORTAL_ROW.format(portal=portal, mode=MODE_OFF if off else MODE_ON)


def _rhythm(search: dict) -> list[str]:
    """The window, and the table of portals only when one is off: without it every portal searches (#291)."""
    days = inline(search.get("window"))
    off = set(items(search.get("portalsOff")))
    window = [WINDOW_LINE.format(days=days)] if days else []
    if not off & set(PORTALS):
        return window
    return [*window, "", *PORTAL_HEAD, *(portal_row(p, p in off) for p in PORTALS)]


def _search_apprenticeship(data: dict) -> list[tuple[str, list[str]]]:
    person, search = data.get("person", {}), data.get("searchApprenticeship", {})
    schools = data.get("education", [])
    school = _joined([inline(schools[0].get("studyType")), inline(schools[0].get("institution"))]) if schools else ""
    tests = [f"{inline(c.get('name'))}" + (f" ({inline(c.get('date'))})" if text(c.get("date")) else "")
             for c in data.get("certificates", [])]
    trials = [_joined([inline(w.get("name")), inline(w.get("position"))]) + _period(w, prefix=" (", suffix=")")
              for w in data.get("work", [])]
    return [
        ("Person", _pairs(("Name", person.get("name")), ("Sprache der Antworten", "Deutsch"),
                          ("Begleitperson", search.get("companion")))),
        ("Gesucht", _bullets([inline(search.get("offers"))])),
        ("Lehrbeginn", _bullets([inline(search.get("start"))])),
        ("Berufe (mit Priorität)", _numbered(search.get("professions"))),
        ("Berufswahl", _bullets([inline(search.get("howFound"))])),
        ("Region", _pairs(("Wohnort", search.get("home")), ("Schulweg", search.get("commute")),
                          ("Kantone", _joined(items(search.get("cantons")))), ("Umkreis", search.get("radius")))),
        ("Schule", _bullets([school]) + _pairs(("Berufsmaturität", search.get("vocationalBaccalaureate")))),
        ("Eignungstests", _bullets(tests)),
        ("Schnupperlehren", _bullets(trials)),
        ("Stärken", _bullets([_joined(_strength_names(data))])),
        ("Typische Haken (offen benennen)", _gaps(data)),
        ("Quellen", _bullets(APPRENTICESHIP_SOURCES)),
    ]


def style_profile(form: dict, data: dict, track: str, note: str) -> str:
    style = data.get("style", {})
    letter = "Motivationsschreiben" if track == "apprenticeship" else "Anschreiben"
    if track == "apprenticeship" or style.get("address") == "Immer Sie-Form":
        salutation = [f"Immer {SALUTATION_FORMAL}"]
    else:
        salutation = [SALUTATION_INFORMAL, f"Sonst {SALUTATION_FORMAL}"]
    greeting = inline(style.get("greeting")) or DEFAULT_GREETING
    place = inline(style.get("place"))
    salutation.append(f"Gruss: „{greeting}“" + (f"; Ort im Datum: {place}." if place else "."))
    outline = APPRENTICESHIP_OUTLINE if track == "apprenticeship" else JOB_OUTLINE
    phrases = [f"Einstieg: „{inline(style.get('opening'))}“", f"Schluss: „{inline(style.get('closing'))}“"]
    phrases += [f"„{inline(p)}“" for p in items(style.get("phrases"))]
    intro = (f"{note}. Gilt für jedes {letter}. Bei Konflikten geht ein professioneller, "
             "zur Firma passender Ton vor dem persönlichen Stil.")
    return _document("# Stilprofil", intro, [
        ("Ton", _bullets([f"{inline(style.get('tone'))}.",
                          "Aussagen mit konkreten Beispielen belegen; Lücken offen und knapp benennen, mit Lernbereitschaft.",
                          "Schweizer Schreibweise (ss statt ß)."])),
        ("Anrede und Form", _bullets(salutation)),
        ("Aufbau (eine Seite)", [f"{n}. {line}" for n, line in enumerate(outline, 1)]),
        ("Typische Formulierungen", _bullets(phrases)),
    ])


def building_blocks(data: dict, track: str, note: str) -> str:
    stations = [_block(", ".join(filter(None, [inline(w.get("position")), inline(w.get("name")), inline(w.get("location"))]))
                       + _period(w, prefix=" (", suffix=")"),
                       "; ".join(inline(h) for h in highlight_texts(w.get("highlights"))), w.get("evidence"))
                for w in data.get("work", [])]
    strengths = [_block(inline(s.get("strength")), inline(s.get("example")), s.get("evidence"))
                 for s in data.get("strengths", [])]
    frame = data.get("frame", {})
    available = "Schnuppern möglich" if track == "apprenticeship" else "Verfügbar ab"
    available_value = frame.get("availability") if track == "apprenticeship" else _job_start(data)
    how_found = inline(data.get("searchApprenticeship", {}).get("howFound")) if track == "apprenticeship" else ""
    letter = "Motivationsschreiben" if track == "apprenticeship" else "Anschreiben"
    intro = f"{note}. Jede Aussage, die in ein {letter} darf, steht hier einmal, mit Beleg."
    return _document("# Bausteine fürs Anschreiben", intro, [
        ("Schnupperlehren und Erfahrungen" if track == "apprenticeship" else "Stationen", stations),
        ("Stärken", strengths),
        ("Berufswahl", _bullets([how_found])),
        ("Lücken (offen benennen)", _gaps(data)),
        ("Rahmen", _pairs((available, available_value), ("Kündigungsfrist", frame.get("notice")),
                          ("Lohnvorstellung", frame.get("salary")), ("Referenz", frame.get("reference")))),
    ])


def _job_start(data: dict):
    """„Verfügbar ab“ is no longer asked for jobs (#218): a value from before stays, otherwise frühester Start counts."""
    given = data.get("frame", {}).get("availability")
    return given if inline(given) else data.get("searchJob", {}).get("start")


def _block(title: str, body: str, evidence) -> str:
    source = inline(evidence) or OWN_STATEMENT
    body_part = f" {body}." if body and not body.endswith((".", "!", "?")) else (f" {body}" if body else "")
    return f"- **{title}** –{body_part} *Beleg: {source}.*"


def _period(entry: dict, prefix: str = "", suffix: str = "") -> str:
    start, end = inline(entry.get("startDate")), inline(entry.get("endDate"))
    if not start:
        return ""
    return f"{prefix}{start}–{end}{suffix}" if end and end != start else (
        f"{prefix}{start}{suffix}" if end else f"{prefix}seit {start}{suffix}")


def _languages(data: dict) -> list[str]:
    return [f"{inline(lang.get('language'))} ({inline(lang.get('fluency'))})" for lang in data.get("languages", [])]


def _strength_names(data: dict) -> list[str]:
    return [inline(s.get("strength")) for s in data.get("strengths", []) if text(s.get("strength"))]


def _education_summary(data: dict) -> str:
    return "; ".join(_joined([inline(e.get("studyType")), inline(e.get("area")), inline(e.get("institution"))])
                     for e in data.get("education", []))


def _numbered(values) -> list[str]:
    return [f"{n}. {inline(v)} (Priorität {n})" for n, v in enumerate(items(values), 1)]


def _pairs(*pairs: tuple[str, object]) -> list[str]:
    return [f"- {label}: {inline(value)}" for label, value in pairs if inline(value)]


def _gaps(data: dict) -> list[str]:
    """Known gaps, or a note that they are added later (they are rarely known at the start)."""
    return _bullets(items(data.get("gaps", {}).get("gaps"))) or [GAPS_LATER]


def _bullets(values: list[str]) -> list[str]:
    return [f"- {inline(v)}" for v in values if inline(v)]


def _joined(values: list[str]) -> str:
    return ", ".join(v for v in values if v)


def _document(title: str, intro: str, sections: list[tuple[str, list[str]]]) -> str:
    blocks = [title, intro] + ["\n".join([f"## {name}", *lines]) for name, lines in sections if lines]
    return "\n\n".join(blocks) + "\n"
