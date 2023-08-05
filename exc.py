from typing import Iterable


class BlottoRoundToGameRoundTranslationError(Exception):
    def __init__(self, missing: Iterable):
        self.message = (
            f"BlottoRound failed to generate GameRound due to missing keys: {missing}"
        )

    def __str__(self):
        return self.message


class BlottoRoundNotImplementedError(Exception):
    def __init__(self, missing: Iterable):
        self.message = (
            f"Subclass of BlottoRound is missing the following attributes: {missing}"
        )
