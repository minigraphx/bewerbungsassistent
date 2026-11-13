"""Small helpers for reading values from a validated bundle."""
LANGUAGES = ("de", "en")  # of a two-language value {de, en}


def text(value) -> str:
    """Trimmed text; None and blanks become an empty string. Of a value in two languages (G30) the German text, or
    the English one without it: the Markdown basics are written in German."""
    if isinstance(value, dict) and value and set(value) <= set(LANGUAGES):
        return next((text(value[key]) for key in LANGUAGES if text(value.get(key))), "")
    return value.strip() if isinstance(value, str) else ""


def items(values) -> list[str]:
    """Non-empty, trimmed list entries."""
    return [v.strip() for v in values or [] if isinstance(v, str) and v.strip()]


def highlight_texts(values) -> list[str]:
    """Non-empty, trimmed texts of highlights, which are text or {text, tags} (G24), in two languages too (G30)."""
    texts = (text(v.get("text") if isinstance(v, dict) and "text" in v else v) for v in values or [])
    return [line for line in texts if line]
