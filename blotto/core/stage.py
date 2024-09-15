"""
Constraints on how players may allocate soldiers to fields on a stage.
"""
import logging
import random
from typing import Self

from blotto.core.library import BlottoLibrary
from blotto.exc import (
    BlottoNotDefinedError,
    BlottoValidationError,
)

logging.basicConfig(level=logging.INFO)


class Stage:
    """Framework for implementing new Stage rules for Blotto.

    Stage defines a construct that manages constraints placed on players during a
    BlottoRound.

    This base class defines what each new Stage variant must be able to do and what
    characteristics must be provided. A Stage cannot exist without at least a number
    of fields and soldiers.

    Attributes:
    - LIBRARY_ID (int): the Blotto StageLibrary ID for lookups
    - RULES (str): a text string that explains the Stage rules
    - fields (int): the number of fields in a BlottoRound instance
    - soldiers (int): the number of soliders in a BlottoRound instance
    """

    LIBRARY_ID: int = None
    RULES: str = None
    _field_bounds: tuple[int, int] = None
    _soldier_bounds: tuple[int, int] = None

    def __init__(
        self,
        fields: int,
        soldiers: int,
    ):
        """
        Instances of `BlottoRound` require at least that `soldiers` and `fields` be
        defined.

        If not using an existing BlottoRound or GameRound configuration, create new
        instances using `from_new` instead, which will randomly select the number of
        fields and soldiers for the round.
        """

        self._fields = fields
        self._soldiers = soldiers

        must_implement = [
            "LIBRARY_ID",
            "RULES",
            "_field_bounds",
            "_soldier_bounds",
        ]
        missing = []
        for attr in must_implement:
            try:
                getattr(self, attr)
            except AttributeError:
                missing.append(attr)

        if missing:
            raise BlottoNotDefinedError(missing)

    @classmethod
    def from_new(cls: Self) -> Self:
        """Returns a Stage with random configuration.

        Each Stage variant should define a construction algorithm
        and constraints that make sense, but a basic implementation
        is provided for convenience.
        """
        fields = cls._random_fields()
        soldiers = cls._random_soldiers()

        return cls(fields, soldiers)

    def check_stage_rules(self, submission: list[int]):
        """Validates a user submission according to general Stage rules.

        For example, participants may never allocate more soldiers
        than they have available.

        Raises:
            BlottoValidationError on any rule violation.
        """
        if sum(submission) > self.soldiers:
            raise BlottoValidationError("Total soldiers is too high")

        if len(submission) > self.fields:
            raise BlottoValidationError("Total fields is too high")

        if any([soldiers < 0 for soldiers in submission]):
            raise BlottoValidationError("Soldiers in a field cannot be negative")

        if any([not isinstance(soldiers, int) for soldiers in submission]):
            raise BlottoValidationError(
                "All fields must have an integer number of soldiers"
            )

    def check_field_rules(self, submission: list[int]) -> dict[str, str]:
        """Validates a user submission according to round rules.

        Args:
            submission: a list representing fields, with each element
            representing the number of soldiers allocated.

        Returns:
            A dictionary of `{field_number (int): validation_error (str)}` that
            describes the issues with a user's submission.
        """
        raise NotImplementedError

    @property
    def fields(self):
        return self._fields

    @property
    def soldiers(self):
        return self._soldiers

    @classmethod
    def _random_fields(cls) -> int:
        """Returns a random number of fields within certain bounds.

        Should be implemented by each subclass of BlottoRound in a way
        that makes sense in the context of the round's rules.
        """
        raise NotImplementedError

    @classmethod
    def _random_soldiers(cls) -> int:
        """Returns a random number of soldiers within certain bounds.

        Should be implemented by each subclass of BlottoRound in a way
        that makes sense in the context of the round's rules.
        """
        raise NotImplementedError


class TestRound(Stage):
    LIBRARY_ID = 0
    RULES = """This is an example of round rules.
• This is a bullet point
• A validation error should appear on all fields if total soldiers is not 100
• A validation error should appear on Field 1 if the input value is not 8
• Otherwise, the submission will succeed

RULES must be Markdown-friendly.
"""

    def check_field_rules(self, submission: list[int]) -> dict[str, str]:
        errors = {}

        for i, soldiers in enumerate(submission):
            field = i + 1

            if i == 0 and soldiers != 8:
                errors[field] = "Field 1 must have 8 soldiers"

        return errors

    def check_stage_rules(self, submission: list[int]):
        if sum(submission) > self.soldiers:
            raise BlottoValidationError("Total soldiers too high")

        if sum(submission) < self.soldiers:
            raise BlottoValidationError("Total soldiers too low")

        if len(submission) != self.fields:
            raise BlottoValidationError("Number of fields is incorrect")

        if any([soldiers < 0 for soldiers in submission]):
            raise BlottoValidationError("Negative soldiers disallowed")

        if any([not isinstance(soldiers, int) for soldiers in submission]):
            raise BlottoValidationError("Integer number of soldiers only")

    @classmethod
    def _random_fields(cls) -> int:
        return 5

    @classmethod
    def _random_soldiers(cls) -> int:
        return 100


class DecreasingSoldiers(Stage):
    """
    This round can also be interpreted as Increasing soldiers, if fields are viewed in backwards order.
    """  # noqa: E501

    LIBRARY_ID = 1
    RULES = """All submissions must exhibit a decreasing number of soldiers in each next field.

For example, if you allocate 10 soldiers in Field 1, Field 2 may have no more than 10 soldiers.
"""  # noqa: E501

    @classmethod
    def _random_fields(cls) -> int:
        return random.randint(5, 10)

    @classmethod
    def _random_soldiers(cls) -> int:
        return random.randint(16, 25) * 5

    def check_field_rules(self, submission: list[int]) -> dict[str, str]:
        errors = {}
        for i, soldiers in enumerate(submission):
            if i > 0:
                if soldiers > submission[i - 1]:
                    errors[i + 1] = f"Must be fewer soldiers than Field {i}"

        return errors


class DecreasingSoldiersSplit(DecreasingSoldiers):
    LIBRARY_ID = 2
    RULES = """
All submissions must exhibit a decreasing number of soldiers in each next field, except
for one break point at just after the half number of fields.

For example, in a round with 7 fields, and a break point of Field 4:
• Field 4 must have less than Field 3 (and each field before)
• Field 5, however, may have more soldiers than Field 4
• Fields 6 and 7 must then have fewer soldiers than the respective field prior
"""

    def check_field_rules(self, submission: list[int]) -> dict[str, str]:
        errors = {}
        for i, soldiers in enumerate(submission):
            if i > 0 and i != self.fields // 2 + 1:
                if soldiers > submission[i - 1]:
                    errors[i + 1] = f"Must be fewer soldiers than Field {i}"

        return errors


class EvenSoldiers(Stage):
    LIBRARY_ID = 3
    RULES = """
All submissions must exhibit an even number of soldiers in each field.

Additionally, deploying soldiers to a field will cost 1 point per field,
but deploying more than 1 soldier to a field will only ever cost 1 point.

Scoring will be as follows:
• In each field, score will be equal to:
    • 3 for the participant with a higher number of soldiers
"""

    @classmethod
    def _random_fields(cls) -> int:
        return random.randint(3, 7)

    @classmethod
    def _random_soldiers(cls) -> int:
        return random.randint(10, 20) * 5

    def check_field_rules(self, submission: list[int]) -> dict[str, str]:
        errors = {}
        for i, soldiers in enumerate(submission):
            if soldiers % 2 != 0:
                errors[i + 1] = "Must be an even number of soldiers"

        return errors


StageLibrary = BlottoLibrary(Stage)
