"""The error every import step raises when a file cannot be imported."""


class ImportRejected(Exception):
    """The file cannot be imported; `messages` explains why, in German, one line per problem."""

    def __init__(self, messages: list[str]) -> None:
        super().__init__("\n".join(messages))
        self.messages = messages
