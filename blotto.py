from typing import Any, Union, List, Dict
import random
import logging

logging.basicConfig(level=logging.INFO)


class BlottoRound:
    def __init__(self, fields: int, soldiers: int):
        if fields is None or soldiers is None:
            raise ValueError("Args [fields, soldiers] must not be None")

        self._fields = fields
        self._soldiers = soldiers

    @property
    def fields(self):
        return self._fields

    @property
    def soldiers(self):
        return self._soldiers


class DecreasingSoldiers(BlottoRound):
    """
    This round can also be interpreted as Increasing soldiers, if fields are viewed in backwards order.
    """

    ID = 1
    DIFFICULTY = 1
    RULES = """
    All submissions must exhibit a decreasing number of soldiers in each next field.
    That is, if in Field 1, you wish to allocate 10 soldiers, Field 2 may have no more than 10 soldiers.

    Scoring will be as follows:
    * In each field, score will be equal to:
        * The difference in soldiers for the person with more soldiers
        * 0 for the person with less soldiers
    """

    def __init__(
        self, fields: Union[int, None] = None, soldiers: Union[int, None] = None
    ):
        """
        This class can be used to "load" an existing configuration or generate a new one.
        """
        if fields is None and soldiers is None:
            fields = random.randint(3, 7)
            soldiers = random.randint(6, 20) * 5

        elif fields is not None and soldiers is not None:
            pass

        else:
            raise ValueError(
                "If one of [fields, soldiers] is provided, both must be provided."
            )

        super().__init__(fields, soldiers)

    def check_field_rules(self, submission: List[int]):
        """
        This round enforces that fields submitted must have non-increasing numbers of soldiers in fields.

        If, in Field 1, there are 10 soldiers, then Field 2 must contain no more than 9, and Field 3 no more than 8, and so on.

        No field may have a non-integer submission. No field may have a negative submission.

        This method should only be used by loaded configurations.
        """
        if sum(submission) > self.soldiers:
            raise ValueError(f"Submitted soldiers must total less than {self.soldiers}")
        for field, soldiers in enumerate(submission):
            if type(soldiers) is not int:
                raise ValueError(
                    f"Error on Field {field}: all submissions must be integer values"
                )
            if soldiers < 0:
                raise ValueError(
                    f"Error on Field {field}: all submissions must be positive values"
                )
            if field > 0:
                if soldiers > submission[field - 1]:
                    raise ValueError(
                        f"Error on Field {field}: decreasing soldiers criteria not met"
                    )

    def score_opponents(
        self,
        submission_one: Dict[str, Union[str, List]],
        submission_two: Dict[str, Union[str, List]],
    ):
        """
        Takes two valid user submissions as dicts. Positional arguments because order is unimportant.

        Submissions should be a dict like {'user_id': user_id, 'submission': list[field1, field2, ...]}

        Returns the same dicts with the score as an additional key-value pair.
        """
        score_one = 0
        score_two = 0
        for i in range(self.fields):
            soldiers_one = submission_one["submission"][i]
            soldiers_two = submission_two["submission"][i]

            score_one += max(0, soldiers_one - soldiers_two)
            score_two += max(0, soldiers_two - soldiers_one)

        submission_one["score"] = score_one
        submission_two["score"] = score_two

        return submission_one, submission_two


class RoundLibrary:
    # [id]: [round object reference] pairs
    ROUND_MAP = {DecreasingSoldiers.ID: DecreasingSoldiers}

    @classmethod
    def load_round(cls, round_id: int, fields: int, soldiers: int):
        return cls.ROUND_MAP[round_id](fields, soldiers)

    @classmethod
    def get_random(cls):
        return random.choice(list(cls.ROUND_MAP.values()))()
