"""Structured user errors, independent of the GUI and translation catalogs."""


class UserMessageError(Exception):
    def __init__(self, message: str, **values: object) -> None:
        self.message = message
        self.values = values
        super().__init__(message.format(**values))


class InputError(UserMessageError, ValueError):
    pass


class OutputExistsError(UserMessageError, FileExistsError):
    pass
