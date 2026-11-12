"""Whether an SVG may be the logo of the dossier (G18): no script, nothing from outside, nothing the check cannot see.

The file is parsed as XML before it is used. A DOCTYPE, an entity or a processing instruction such as a style sheet is
refused before anything is expanded or fetched, and so is a file that is not well-formed. Elements and attributes count
by their local name, so a prefix like <s:script> or s:onload changes nothing. Links may only point inside the file or
to an embedded PNG, JPG, GIF or WebP; the same holds for url() in styles.
"""
import re
import xml.parsers.expat

SCRIPT = "Dieses SVG enthält ein Skript. Bitte das Logo als PNG speichern und nochmals wählen."
REMOTE = "Dieses SVG lädt Inhalte aus dem Internet. Bitte das Logo als PNG speichern und nochmals wählen."
UNCHECKABLE = "Dieses SVG lässt sich nicht sicher prüfen. Bitte das Logo als PNG speichern und nochmals wählen."

ACTIVE_ELEMENTS = {"script", "foreignobject", "handler", "listener", "iframe", "embed", "object"}
ANIMATIONS = {"set", "animate", "animatecolor", "animatemotion", "animatetransform"}
ANIMATED_VALUES = ("to", "from", "by", "values")
LINKS = {"href", "src", "base"}  # base: xml:base changes where relative links point
SCRIPT_SCHEMES = ("javascript:", "vbscript:")
CSS_ACTIVE = ("javascript:", "vbscript:", "expression(", "behavior:", "-moz-binding")
RASTER_DATA = re.compile(r"data:image/(?:png|jpe?g|gif|webp)[;,]")
CSS_URL = re.compile(r"url\((['\"]?)(.*?)\1\)")
INVISIBLE = re.compile(r"[\s\x00-\x1f]+")

# The DOCTYPEs of SVG 1.0 and 1.1 as editors export them (#243): public id → the file name of its DTD at the W3C
SVG_DTDS = {
    "-//W3C//DTD SVG 1.0//EN": "www.w3.org/TR/2001/REC-SVG-20010904/DTD/svg10.dtd",
    "-//W3C//DTD SVG 1.1//EN": "www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd",
    "-//W3C//DTD SVG 1.1 Basic//EN": "www.w3.org/Graphics/SVG/1.1/DTD/svg11-basic.dtd",
    "-//W3C//DTD SVG 1.1 Tiny//EN": "www.w3.org/Graphics/SVG/1.1/DTD/svg11-tiny.dtd",
}
# What may stand before a DOCTYPE: a byte order mark, the XML declaration, comments and white space
PROLOG = re.compile(r"\ufeff?(?:<\?xml\s[^?>]*\?>)?(?:\s|<!--(?:(?!--).)*-->)*", re.S)
# Only the plain forms: no internal subset, since the declaration has to end right after its ids
DOCTYPE = re.compile(r"<!DOCTYPE\s+svg"
                     r"(?:\s+PUBLIC\s+(?P<q1>[\"'])(?P<public>[^\"']*)(?P=q1)\s+(?P<q2>[\"'])(?P<system>[^\"']*)(?P=q2)"
                     r"|\s+SYSTEM\s+(?P<q3>[\"'])(?P<only_system>[^\"']*)(?P=q3))?\s*>")


class Refused(Exception):
    """Stops the parse at the first problem; the message is for the person."""


def _local(name: str) -> str:
    return name.rsplit(":", 1)[-1].lower()


def _flat(value: str) -> str:
    """Lowercase without whitespace or control characters, which browsers skip inside a scheme like java\tscript:."""
    return INVISIBLE.sub("", value).lower()


def link_problem(value: str) -> str | None:
    """A link target: only inside the file or an embedded raster image."""
    target = _flat(value)
    if target.startswith(SCRIPT_SCHEMES):
        return SCRIPT
    if target == "" or target.startswith("#") or RASTER_DATA.match(target):
        return None
    return UNCHECKABLE if target.startswith("data:") else REMOTE


def css_problem(text: str) -> str | None:
    """Style text from a style attribute, a <style> element or a presentation attribute like fill."""
    css = _flat(text)
    if any(sign in css for sign in CSS_ACTIVE):
        return SCRIPT
    if "\\" in css:  # CSS escapes could spell url( or a scheme in a way this check does not read
        return UNCHECKABLE
    if "@import" in css:
        return REMOTE
    return next((p for m in CSS_URL.finditer(css) if (p := link_problem(m.group(2)))), None)


def _attribute_problem(name: str, value: str) -> str | None:
    local = _local(name)
    if name == "xmlns" or name.startswith("xmlns:"):
        return None
    if local.startswith("on"):
        return SCRIPT
    if local in LINKS:
        return link_problem(value)
    if _flat(value).startswith(SCRIPT_SCHEMES):
        return SCRIPT
    return css_problem(value) if local == "style" or "url(" in value.lower() else None


def _animation_problem(attributes: dict) -> str | None:
    """<set attributeName="href" to="https://…"> sets a link as much as href itself."""
    if _local(attributes.get("attributeName", "")) not in LINKS:
        return None
    values = [part for key in ANIMATED_VALUES for part in attributes.get(key, "").split(";")]
    return next((p for v in values if v.strip() and (p := link_problem(v))), None)


class _Checker:
    def __init__(self):
        self.style_depth = 0
        self.style_text = []

    def start(self, name: str, attributes: dict) -> None:
        local = _local(name)
        if local in ACTIVE_ELEMENTS:
            raise Refused(SCRIPT)
        problem = next((p for key, value in attributes.items() if (p := _attribute_problem(key, value))), None)
        problem = problem or (_animation_problem(attributes) if local in ANIMATIONS else None)
        if problem:
            raise Refused(problem)
        self.style_depth += local == "style"

    def end(self, name: str) -> None:
        if _local(name) == "style":
            self.style_depth -= 1
            if problem := css_problem("".join(self.style_text)):
                raise Refused(problem)
            self.style_text = []

    def text(self, data: str) -> None:
        if self.style_depth:
            self.style_text.append(data)


def _refuse(*_) -> None:
    raise Refused(UNCHECKABLE)


def _known_dtd(system: str) -> bool:
    return any(system in (f"http://{dtd}", f"https://{dtd}") for dtd in SVG_DTDS.values())


def _plain(doctype: re.Match) -> bool:
    public, system = doctype.group("public"), doctype.group("system")
    if public is not None:
        return public in SVG_DTDS and system in (f"http://{SVG_DTDS[public]}", f"https://{SVG_DTDS[public]}")
    only_system = doctype.group("only_system")
    return only_system is None or _known_dtd(only_system)


def without_doctype(text: str) -> str:
    """The SVG without its DOCTYPE when that is a plain SVG 1.0 or 1.1 one, as older editors export it.

    Any other DOCTYPE stays, so problem() refuses the file as before; problem() itself still refuses every DOCTYPE.
    Nothing in a plain one is used: it declares no entity, and its DTD only names the SVG elements."""
    prolog = PROLOG.match(text)
    doctype = DOCTYPE.match(text, prolog.end())
    if doctype is None or not _plain(doctype):
        return text
    return text[:doctype.start()] + text[doctype.end():]


def problem(text: str) -> str | None:
    """Why an SVG may not be the logo, or None."""
    checker = _Checker()
    parser = xml.parsers.expat.ParserCreate()
    parser.SetParamEntityParsing(xml.parsers.expat.XML_PARAM_ENTITY_PARSING_NEVER)
    parser.StartDoctypeDeclHandler = _refuse
    parser.EntityDeclHandler = _refuse
    parser.ProcessingInstructionHandler = _refuse
    parser.ExternalEntityRefHandler = _refuse
    parser.StartElementHandler = checker.start
    parser.EndElementHandler = checker.end
    parser.CharacterDataHandler = checker.text
    try:
        parser.Parse(text, True)
    except Refused as refused:
        return str(refused)
    except (xml.parsers.expat.ExpatError, ValueError):
        return UNCHECKABLE
    return None
