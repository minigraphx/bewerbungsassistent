"""A message for the person, T (#414, #422): its own module without the app's settings.

`ui_texts` gives it to the routes; modules that `language_settings` itself reads (`search_plan` through `precheck`)
import it from here, so no import goes round in a circle.
"""
import functools
import re
from typing import Any, Mapping, Sequence

import translation_catalog

PLACEHOLDER = re.compile(r"\{(\w+)\}")
LETTER = re.compile(r"[^\W\d_]")


def has_words(template: str) -> bool:
    """Whether a template says anything besides its placeholders, punctuation and spaces."""
    return bool(LETTER.search(PLACEHOLDER.sub("", template)))


def fill(template: str, values: Mapping[str, Any]) -> str:
    """The placeholders with a value filled in; any other brace stays as written, so no German text can break it."""
    return PLACEHOLDER.sub(lambda found: str(values[found[1]]) if found[1] in values else found[0], template)


class T(str):
    """A message for the person: the German text itself, plus the template and values to say it in another language.

    Copies and pickles rebuild it from the German text and then restore template and values from its __dict__."""

    template: str
    _pairs: tuple[tuple[str, Any], ...]

    def __new__(cls, template: str, **values: Any) -> "T":
        message = super().__new__(cls, fill(template, values))
        message.template = template
        message._pairs = tuple(values.items())
        return message

    @property
    def values(self) -> dict[str, Any]:
        return dict(self._pairs)

    def in_language(self, catalog: translation_catalog.Catalog, language: str) -> str:
        """The message from the catalog with its values, a T among them in the same language; German without entry."""
        template = catalog.text(self.template, language)
        if template is None and not has_words(self.template):
            template = self.template  # „{a} {b}“ has nothing to translate, its parts do
        if template is None:
            return str(self)
        values = {name: value.in_language(catalog, language) if isinstance(value, T) else value
                  for name, value in self._pairs}
        return fill(template, values)


def listing(items: Sequence[Any]) -> Any:
    """Items as „a, b und c“, said in the app language with each item, a T among them, in it too (#425).

    One item is itself; joining with a plain ", ".join would keep the quotes of a quoted term German."""
    if len(items) == 1:
        return items[0]
    head = functools.reduce(lambda joined, item: T("{a}, {b}", a=joined, b=item), items[1:-1], items[0])
    return T("{namen} und {letzter}", namen=head, letzter=items[-1])


def joined(parts: Sequence[Any], separator: str = " ") -> Any:
    """Parts one after the other, as `separator.join` would, but each part a T keeps its own language (#433).

    One part is itself, none is the empty text; „{a} {b}“ and „{a}, {b}“ say the same in every language."""
    if not parts:
        return ""
    template = "{a}" + separator + "{b}"
    return functools.reduce(lambda done, part: T(template, a=done, b=part), parts[1:], parts[0])


class Label(T):
    """The label of a field up to its bracket, in every language: „Geburtsdatum (freiwillig)“ names „Geburtsdatum“.

    The catalog holds the whole label, so the cut follows the translation, as `locate` in validate.js does."""

    BRACKET = " ("

    def __new__(cls, template: str) -> "Label":
        message = str.__new__(cls, template.split(cls.BRACKET)[0])
        message.template = template
        message._pairs = ()
        return message

    def in_language(self, catalog: translation_catalog.Catalog, language: str) -> str:
        return super().in_language(catalog, language).split(self.BRACKET)[0]
