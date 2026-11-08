"""The error every import step raises when a file cannot be imported."""


class ImportRejected(Exception):
    """The file cannot be imported; `messages` explains why, in German, one line per problem."""

    def __init__(self, messages: list[str]) -> None:
        super().__init__("\n".join(messages))
        self.messages = messages


class ExistingFiles(ImportRejected):
    """Markdown files that exist already wait for a choice per file (G26); `choice` holds each with its diff."""

    def __init__(self, messages: list[str], choice: list[dict]) -> None:
        super().__init__(messages)
        self.choice = choice
