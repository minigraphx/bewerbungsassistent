"""A refusal of the data in German, with its template and values (#453, #455).

lebenslauf builds on its own and never imports the app, so a refusal carries what the app needs to say it in its own
language (bewerbungen/refusal_messages.py). On the command line it is the German text, byte for byte as before.
"""
import re

PLACEHOLDER = re.compile(r"\{(\w+)\}")


class Refusal(ValueError):
    """German text from a template with {name} placeholders; any other brace, as in „z.B. {mirror: true}“, stays."""

    def __init__(self, template: str, **values: object) -> None:
        super().__init__(PLACEHOLDER.sub(lambda found: str(values[found[1]]) if found[1] in values else found[0],
                                         template))
        self.template = template
        self.values = values
