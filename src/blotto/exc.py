from typing import Iterable


class BlottoRoundToGameRoundTranslationError(Exception):
    def __init__(self, missing: Iterable):
        self.message = (
            f"BlottoRound failed to generate GameRound due to missing keys: {missing}"
        )

    def __str__(self):
        return self.message


class BlottoNotDefinedError(Exception):
    """Describes a Blotto object that is missing required attributes"""

    def __init__(self, obj: object, missing: Iterable):
        self.message = f"{type(obj)} is missing the following attributes: {missing}"


class BlottoNotImplementedError(Exception):
    def __init__(self, obj: type, undefined: str):
        self.message = f"{obj} has not implemented {undefined}"


class BlottoValidationError(Exception):
    def __init__(self, message):
        self.message = message
