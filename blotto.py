import datetime
import logging
import random
from typing import Optional, Self

import db_utils
from exc import (
    BlottoRoundNotImplementedError,
    BlottoRoundToGameRoundTranslationError,
    BlottoValidationError,
)
from models import Game, GameRound

logging.basicConfig(level=logging.INFO)


class BlottoRound:
    """Framework for implementing new rules for Blotto.

    BlottoRound is the application-driving metaclass for rounds. This metaclass
    defines what each new type of round must be able to do and what characteristics
    must be provided. A BlottoRound cannot exist without at least a number of
    fields and soldiers.

    Equally importantly, a BlottoRound is responsible for translating to and from
    instances of GameRound, which represent state for a particular Game. Instantiating
    from an existing GameRound will load the BlottoRound with additional attributes
    defined by the SQLAlchemy model.

    Attributes:
    - LIBRARY_ID (int): the Blotto RoundLibrary ID that specifies the round rules
    - RULES (str): a text string that explains the round rules
    - fields (int): the number of fields in a BlottoRound instance
    - soldiers (int): the number of soliders in a BlottoRound instance
    - game_id (int): an optional Game ID that ties the BlottoRound instance to a
        particular game
    - number (int): an optional value that describes which Round in a Game the
        BlottoRound instance corresponds to
    - start (datetime.datetime): an optional timestamp that indicates when the
        GameRound tied to this BlottoRound starts
    - end (datetime.datetime): an optional timestamp that indicates when the
        GameRound tied to this BlottoRound ends
    """

    LIBRARY_ID: int = None
    RULES: str = None
    _field_bounds: tuple[int, int] = None
    _soldier_bounds: tuple[int, int] = None

    def __init__(
        self,
        fields: int,
        soldiers: int,
        *,
        game_id: Optional[int] = None,
        number: Optional[int] = None,
        start: Optional[datetime.datetime] = None,
        end: Optional[datetime.datetime] = None,
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

        self._game_id = game_id
        self._number = number
        self._start = start
        self._end = end

        must_implement = ["LIBRARY_ID", "RULES", "_field_bounds", "_soldier_bounds"]
        missing = []
        for attr in must_implement:
            try:
                getattr(self, attr)
            except AttributeError:
                missing.append(attr)

        if missing:
            raise BlottoRoundNotImplementedError(missing)

    @classmethod
    def from_new(cls: type[Self]) -> Self:
        """Returns a BlottoRound with random configuration.

        Uses the subclass-specific algorithm to randomly generate
        a number of fields and soldiers.
        """
        fields = cls._random_fields()
        soldiers = cls._random_soldiers()

        return cls(fields, soldiers)

    def to_game_round(self) -> GameRound:
        """Returns a GameRound instance.

        Raises an error if the BlottoRound instance does not define all the necessary
        GameRound attributes.
        """
        attrs = [
            "game_id",
            "number",
            "library_id",
            "start",
            "end",
            "fields",
            "soldiers",
        ]
        vals = {}
        missing = []
        for key in attrs:
            val = getattr(self, key, None)
            vals[key] = val

            if val is None:
                missing.append(key)

        if missing:
            raise BlottoRoundToGameRoundTranslationError(missing)

        return GameRound(**vals)

    def check_general_rules(self, submission: list[int]):
        """Validates a user submission according to general round rules.

        For example, participants may never allocate more soldiers
        than they have available.

        Raises:
            BlottoValidationError on any rule violation. This can vary by
            BlottoRound.
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

    @property
    def game_id(self):
        return self._game_id

    @property
    def number(self):
        return self._number

    @property
    def start(self):
        return self._start

    @property
    def end(self):
        return self._end

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


class TestRound(BlottoRound):
    LIBRARY_ID = 0
    RULES = """This is an example of round rules.
• This is a bullet point
• A validation error should appear on all fields if total soldiers is not 100
• A validation error should appear on Field 1 if the input value is not 8
• Otherwise, the submission will succeed
"""

    def check_field_rules(self, submission: list[int]) -> dict[str, str]:
        errors = {}

        for i, soldiers in enumerate(submission):
            field = i + 1

            if i == 0 and soldiers != 8:
                errors[field] = "Field 1 must have 8 soldiers"

        return errors

    def check_general_rules(self, submission: list[int]):
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


class DecreasingSoldiers(BlottoRound):
    """
    This round can also be interpreted as Increasing soldiers, if fields are viewed in backwards order.
    """  # noqa: E501

    LIBRARY_ID = 1
    RULES = """
> All submissions must exhibit a decreasing number of soldiers in each next field.
>
> For example, if you allocate 10 soldiers in Field 1, Field 2 may have no more than 10 soldiers.
>
> Scoring will be as follows:
> • In each field, score will be equal to:
>     • The difference in soldiers for the person with more soldiers
>     • 0 for the person with less soldiers
"""  # noqa: E501

    @classmethod
    def _random_fields(cls) -> int:
        return random.randint(3, 7)

    @classmethod
    def _random_soldiers(cls) -> int:
        return random.randint(10, 20) * 5

    def check_field_rules(self, submission: list[int]) -> dict[str, str]:
        errors = {}
        for i, soldiers in enumerate(submission):
            if i > 0:
                if soldiers > submission[i - 1]:
                    errors[i + 1] = f"Must be fewer soldiers than Field {i}"

        return errors


class RoundLibrary:
    ROUND_MAP = {
        round.LIBRARY_ID: round
        for round in BlottoRound.__subclasses__()
        if round.LIBRARY_ID != 0  # reserved for a testing round
    }

    @classmethod
    def load_round(
        cls,
        game_round: Optional[GameRound] = None,
        game_id: Optional[int] = None,
        round_number: Optional[int] = None,
    ) -> BlottoRound:
        """Returns the appropriate BlottoRound subclass.

        Requires either:
        - GameRound instance
        - game_id AND round_number
        """
        if game_round is not None:
            pass
        elif game_id is not None and round_number is not None:
            game_round = db_utils.get_game_round(game_id, round_number)
        else:
            raise ValueError(
                "Please provide either: game_round OR (game_id AND round_number)"
            )

        blotto_round = cls.ROUND_MAP[game_round.library_id](
            game_round.fields,
            game_round.soldiers,
            game_id=game_round.game_id,
            number=game_round.number,
            start=game_round.start,
            end=game_round.end,
        )

        return blotto_round

    @classmethod
    def get_random(cls) -> type[BlottoRound]:
        return random.choice(list(cls.ROUND_MAP.values()))


class GameFactory:
    @staticmethod
    def new_game(
        user_id: str,
        num_rounds: int,
        round_length: datetime.timedelta,
        start: datetime.datetime,
    ) -> Game:
        """Inserts a new Game record and associated GameRound records to the DB.
        Returns the new Game object.

        args:
        - num_rounds: the number of GameRounds to be created for the new Game
        - round_length: the interval allotted to each GameRound from the rules
        announcement to posting results
        - start: the end of the game signup window, which coincides with the
        time that the first round's rules will be posted
        """
        new_game = Game(
            admin=user_id,
            start=start,
            end=(start + (round_length * num_rounds)),
            num_rounds=num_rounds,
            round_length=round_length,
        )
        db_utils.create_records([new_game])

        new_rounds = []
        for round_num in range(1, num_rounds + 1):
            blotto_round = RoundLibrary.get_random().from_new()
            round_start = start + round_length * (round_num - 1)
            round_end = round_start + round_length

            new_round = GameRound(
                game_id=new_game.id,
                number=round_num,
                library_id=blotto_round.LIBRARY_ID,
                start=round_start,
                end=round_end,
                fields=blotto_round.fields,
                soldiers=blotto_round.soldiers,
            )
            new_rounds.append(new_round)

        db_utils.create_records(new_rounds)

        return new_game
