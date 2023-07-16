import datetime
import logging
import random

import db_utils
from models import Engine

logging.basicConfig(level=logging.INFO)


class BlottoRound:
    def __init__(
        self,
        field_bounds: tuple[int],
        soldier_bounds: tuple[int],
        game_id: int,
    ):
        fields = self._random_fields(field_bounds)
        soldiers = self._random_soldiers(soldier_bounds)

        self._fields = fields
        self._soldiers = soldiers
        self._game_id = game_id

    @property
    def fields(self):
        return self._fields

    @property
    def soldiers(self):
        return self._soldiers

    @property
    def game_id(self):
        return self._game_id

    def _random_fields(self, field_bounds: tuple[int, int]) -> int:
        return random.randint(*field_bounds)

    def _random_soldiers(self, soldier_bounds: tuple[int, int]) -> int:
        return random.randint(*soldier_bounds)


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

    def update_results(self):
        """
        Must be an instance of a round that is tied to a game instance.

        Will pull submissions from the database, calculate each user's score, and push the scores to the round_result table.
        """
        submissions = db_utils.get_submissions_dataframe(self.game_id)


class RoundLibrary:
    ROUND_MAP = {DecreasingSoldiers.ID: DecreasingSoldiers}

    @classmethod
    def load_round(
        cls, round_id: int, fields: int, soldiers: int, game_id: int | None = None
    ):
        """
        Must provide a round ID, number of fields, and soldiers.

        Game ID is optional, and useful for object instances that will be used to calculate results.
        """
        return cls.ROUND_MAP[round_id](fields, soldiers, game_id)

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
