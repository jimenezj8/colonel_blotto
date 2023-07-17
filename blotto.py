import datetime
import logging
import random
from typing import Optional, Self

import db_utils
from exc import *  # noqa: F403
from models import Engine, GameRound

logging.basicConfig(level=logging.INFO)


class BlottoRound:
    """Framework for implementing new rules, operating within the application,
    and persisting data to the DB.

    BlottoRound is the application-driving metaclass for rounds. This metaclass
    defines what each new type of round must be able to do and what characteristics
    must be provided. A BlottoRound cannot exist without at least a number of
    fields and soldiers.

    Equally importantly, a BlottoRound is responsible for translating to and from
    instances of GameRound, which represent state for a particular Game. Instantiating
    from an existing GameRound will load the BlottoRound with additional attributes
    defined by the SQLAlchemy model.
    """

    LIBRARY_ID = None
    RULES = None

    def __init__(
        self,
        fields: int,
        soldiers: int,
        *,
        id: Optional[int] = None,
        library_id: Optional[int] = None,
        game_id: Optional[int] = None,
        start_time: Optional[datetime.datetime] = None,
        end_time: Optional[datetime.datetime] = None,
    ):
        """
        Instances of `BlottoRound` require at least that
        `soldiers` and `fields` be defined.

        Use the classmethods `from_*` to create instances.
        """

        self._fields = fields
        self._soldiers = soldiers

        self._id = id
        self._library_id = library_id
        self._game_id = game_id
        self._start_time = start_time
        self._end_time = end_time

        must_implement = ["LIBRARY_ID", "RULES"]
        missing = []
        for attr in must_implement:
            try:
                getattr(self, attr)
            except AttributeError:
                missing.append(attr)

        if missing:
            raise BlottoRoundNotImplementedError(missing)  # noqa: F405

    @classmethod
    def from_id(cls, id: int) -> Self:
        """Creates an instance of `BlottoRound` from a `GameRound` ID

        `from_id` loads `fields` and `rounds` by querying the DB for the `GameRound`.

        If you already have a `GameRound` loaded, use `from_game_round` instead.

        args:
        - id: the `GameRound` ID (primary key for the DB)
        """
        game_round = db_utils.get_game_round(id)

        return cls.from_game_round(game_round)

    @classmethod
    def from_new(
        cls, field_bounds: tuple[int, int], soldier_bounds: tuple[int, int]
    ) -> Self:
        fields = cls._random_fields(*field_bounds)
        soldiers = cls._random_soldiers(*soldier_bounds)

        return cls(fields, soldiers)

    @classmethod
    def from_game_round(cls, game_round: GameRound) -> Self:
        return cls(game_round.fields, game_round.soldiers)

    def to_game_round(self) -> GameRound:
        """Returns a GameRound instance.

        Raises if the BlottoRound instance does not define all the necessary
        GameRound attributes.
        """
        attrs = [
            "id",
            "library_id",
            "game_id",
            "start_time",
            "end_time",
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

    @property
    def fields(self):
        return self._fields

    @property
    def soldiers(self):
        return self._soldiers

    @property
    def id(self):
        return self._id

    @property
    def library_id(self):
        return self._library_id

    @property
    def game_id(self):
        return self._game_id

    @property
    def start_time(self):
        return self._start_time

    @property
    def end_time(self):
        return self._end_time

    def _random_fields(self, field_bounds: tuple[int, int]) -> int:
        return random.randint(*field_bounds)

    def _random_soldiers(self, soldier_bounds: tuple[int, int]) -> int:
        return random.randint(*soldier_bounds)


class DecreasingSoldiers(BlottoRound):
    """
    This round can also be interpreted as Increasing soldiers,
    if fields are viewed in backwards order.
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
"""  # noqa: E501

    def __init__(
        self,
        fields: int | None = None,
        soldiers: int | None = None,
        game_id: int | None = None,
    ):
        field_bounds = (3, 7)
        soldier_bounds = (30, 100)

        super().__init__(fields, soldiers, field_bounds, soldier_bounds, game_id)

    def check_field_rules(self, submission: list[int]) -> dict[str, str]:
        """
        This round enforces that fields submitted must have non-increasing numbers
        of soldiers in fields.

        If, in Field 1, there are 10 soldiers, then Field 2 must contain no
        more than 9, and Field 3 no more than 8, and so on.

        No field may have a non-integer submission.
        No field may have a negative submission.

        This method should only be used by loaded configurations.
        It returns a dictionary of field-specific errors for
        usage in responding to users.
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

    def update_results(self):
        """
        Must be an instance of a round that is tied to a game instance.

        Will pull submissions from the database, calculate each user's score, and push the
        scores to the round_result table.
        """  # noqa: E501
        submissions = db_utils.get_submissions_dataframe(self.game_id)


class RoundLibrary:
    ROUND_MAP = {round.ID: round for round in BlottoRound.__subclasses__()}

    @classmethod
    def load_round(cls, round_id: int) -> Self:
        """Using a Round ID, creates an instance of BlottoRound from the corresponding
        GameRound.
        """
        return cls.ROUND_MAP[round_id].from_id(round_id)

    @classmethod
    def get_random(cls):
        return random.choice(list(cls.ROUND_MAP.values()))()


class GameFactory:
    @classmethod
    def new_game(
        cls,
        num_rounds: int,
        round_length: datetime.timedelta,
        start: datetime.datetime,
    ) -> int:
        game_id = db_utils.create_new_game(num_rounds, round_length, start)

        new_rounds = []
        for round_num in range(num_rounds):
            new_round = RoundLibrary.get_random()
            new_rounds.append(
                {
                    "id": new_round.ID,
                    "game_id": game_id,
                    "number": round_num + 1,
                    "start": start + round_length * round_num,
                    "end": start + round_length * (round_num + 1),
                    "fields": new_round.fields,
                    "soldiers": new_round.soldiers,
                    "canceled": False,
                }
            )

        db_utils.create_new_rounds(new_rounds)

        return game_id


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
