"""Small helpers for reading values from a validated bundle."""


def text(value) -> str:
    """Trimmed text; None and blanks become an empty string."""
    return value.strip() if isinstance(value, str) else ""


def items(values) -> list[str]:
    """Non-empty, trimmed list entries."""
    return [v.strip() for v in values or [] if isinstance(v, str) and v.strip()]


def highlight_texts(values) -> list[str]:
    """Non-empty, trimmed texts of highlights, which are text or {text, tags} (G24)."""
    return items(v.get("text") if isinstance(v, dict) else v for v in values or [])
