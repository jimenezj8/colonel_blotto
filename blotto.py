import datetime
import logging
import random
from typing import Optional, Self

from slack_sdk.models.views import ViewStateValue

import db_utils
from exc import *  # noqa: F403
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
            raise BlottoRoundNotImplementedError(missing)  # noqa: F405

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
            raise BlottoRoundToGameRoundTranslationError(missing)  # noqa: F405

        return GameRound(**vals)

    @classmethod
    def check_field_rules(
        cls, input_blocks: dict[str, dict[str, ViewStateValue]]
    ) -> dict[str, str]:
        """Validates a user submission according to round rules.

        Args:
            input_blocks: a dictionary of block labels to elements, which are themselves
                dictionaries of element labels to state values.

        Returns:
            A dictionary of `{field_label: validation_error}` that describes
            the issues with a user's submission.
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
• A validation error should appear on Field 1 if the input value is not 8
• Otherwise, the submission will succeed
"""

    @classmethod
    def check_field_rules(
        self, input_blocks: dict[str, dict[str, ViewStateValue]]
    ) -> dict[str, str]:
        errors = {}

        for i, (block_id, block) in enumerate(input_blocks.items()):
            state_value = block[block_id.replace("block", "element")]

            if i == 0 and int(state_value.value) != 8:
                errors[block_id] = "Field 1 must have 8 soldiers"

        return errors

    @classmethod
    def _random_fields(cls) -> int:
        return 5

    @classmethod
    def _random_soldiers(cls) -> int:
        return 100


class DecreasingSoldiers(BlottoRound):
    """
    This round can also be interpreted as Increasing soldiers, if fields are viewed in backwards order.
    """

    ID = 1
    DIFFICULTY = 1
    RULES = """
> All submissions must exhibit a decreasing number of soldiers in each next field.
>
> For example, if you allocate 10 soldiers in Field 1, Field 2 may have no more than 10 soldiers.
>
> Scoring will be as follows:
> • In each field, score will be equal to:
>     • The difference in soldiers for the person with more soldiers
>     • 0 for the person with less soldiers
"""

    def __init__(
        self,
        fields: int | None = None,
        soldiers: int | None = None,
        game_id: int | None = None,
    ):
        """
        This class can be used to "load" an existing configuration or generate a new one.
        """
        field_bounds = (3, 7)
        soldier_bounds = (30, 100)

        super().__init__(fields, soldiers, field_bounds, soldier_bounds, game_id)

    def check_field_rules(self, submission: list[int]) -> dict[str, str]:
        """
        This round enforces that fields submitted must have non-increasing numbers of soldiers in fields.

        If, in Field 1, there are 10 soldiers, then Field 2 must contain no more than 9, and Field 3 no more than 8, and so on.

        No field may have a non-integer submission. No field may have a negative submission.

        This method should only be used by loaded configurations. It returns a dictionary of field-specific errors for usage in responding to users.
        """
        if sum(submission) > self.soldiers:
            raise ValueError(f"Submitted soldiers must total less than {self.soldiers}")

        errors = {}
        for field, soldiers in enumerate(submission):
            if soldiers < 0:
                errors[f"field-{field+1}"] = "Must be positive value"

            if field > 0:
                if soldiers > submission[field - 1]:
                    errors[
                        f"field-{field+1}"
                    ] = f"Must be fewer soldiers than Field {field}"

        return errors


class RoundLibrary:
    ROUND_MAP = {round.LIBRARY_ID: round for round in BlottoRound.__subclasses__()}

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
    def get_random(cls):
        return random.choice(list(cls.ROUND_MAP.values()))()


class GameFactory:
    @staticmethod
    def new_game(
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
            start=start,
            end=(start + (round_length * num_rounds)),
            num_rounds=num_rounds,
            round_length=round_length,
        )

        new_rounds = []
        for round_num in range(1, num_rounds + 1):
            blotto_round = RoundLibrary.get_random()
            round_start = start + round_length * (round_num - 1)
            round_end = round_start + round_length

            new_round = GameRound(
                game_id=new_game.id,
                number=round_num,
                library_id=blotto_round.ID,
                start=round_start,
                end=round_end,
                fields=blotto_round.fields,
                soldiers=blotto_round.soldiers,
            )
            new_rounds.append(new_round)

        db_utils.create_records([new_game] + new_rounds)

        return new_game.id


def update_game_results(game_id: int) -> None:
    round_results = db_utils.get_round_results_dataframe(game_id)

    game_results = round_results.groupby(by="user_id", as_index=False).agg(
        {"score": "mean"}
    )
    game_results["game_id"] = game_id
    game_results.sort_values(by="score", ascending=False, inplace=True)
    game_results = (
        game_results.reset_index(drop=True)
        .reset_index(drop=False)
        .rename(columns={"index": "rank"})
    )
    game_results.to_sql("game_result", Engine, if_exists="append")
