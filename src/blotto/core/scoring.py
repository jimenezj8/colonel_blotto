from blotto.core.library import BlottoLibrary
from blotto.exc import BlottoNotImplementedError


class Scorer:
    """Scorer is responsible for handling scoring for all Blotto rounds.

    Subclasses implement the particular scoring methodologies that
    can be used at random with any given round.
    """

    DESCRIPTION: str = None

    @classmethod
    def get_participant_score(
        cls,
        participant_submission: list[int],
        other_submissions: list[list[int]],
    ):
        """Returns the round score for a participant's submission.

        Given a participant's submission, and the complete set of all
        others' submissions, this method calculates the total score
        for the main participant in a given round.
        """
        score = 0
        for other_submission in other_submissions:
            score += cls.calculate_match_score(participant_submission, other_submission)

        return score

    @classmethod
    def calculate_match_score(
        cls,
        main_submission: list[int],
        other_submission: list[int],
    ) -> float:
        """Returns the score of the main_submission for a particular match.

        Raises a ValueError if the two submissions aren't the same length.
        """
        raise BlottoNotImplementedError(cls, "calculate_match_score")

    @classmethod
    def validate_submissions(
        cls,
        main_submission: list[int],
        other_submission: list[int],
    ):
        "Raise a ValueError if the two submissions aren't the same length."
        if len(main_submission) != len(other_submission):
            raise ValueError("Both submissions must be of equal length")


class DifferenceInSoldiersFloored(Scorer):
    LIBRARY_ID = 1
    DESCRIPTION = """Scoring will be as follows:
• In each field, score will be equal to:
    • For the participant with more soldiers: the difference in soldiers on that field
    • For the participant with fewer soldiers: 0
"""

    @classmethod
    def calculate_match_score(
        cls,
        main_submission: list[int],
        other_submission: list[int],
    ) -> float:
        cls.validate_submissions(main_submission, other_submission)
        points = 0
        for i in range(len(main_submission)):
            points += max(main_submission[i] - other_submission[i], 0)

        return points


class DifferenceInSoldiers(Scorer):
    LIBRARY_ID = 2
    DESCRIPTION = """Scoring will be as follows:
• In each field, score will be equal to the difference in soldiers
• For the participant with fewer soldiers, they will lose points
"""

    @classmethod
    def calculate_match_score(
        cls,
        main_submission: list[int],
        other_submission: list[int],
    ) -> float:
        cls.validate_submissions(main_submission, other_submission)
        points = 0
        for i in range(len(main_submission)):
            points += main_submission[i] - other_submission[i]

        return points


class DifferenceInSoldiersHalvedLoss(Scorer):
    LIBRARY_ID = 3
    DESCRIPTION = """Scoring will be as follows:
• In each field, score will be equal to the difference in soldiers
• For the participant with fewer soldiers, they will lose half the difference
    • If the difference in soldiers is -10, that participant loses 5 points
"""

    @classmethod
    def calculate_match_score(
        cls,
        main_submission: list[int],
        other_submission: list[int],
    ) -> float:
        cls.validate_submissions(main_submission, other_submission)
        points = 0
        for i in range(len(main_submission)):
            points += main_submission[i] - other_submission[i] / 2

        return points


class IncreasingValueByOne(Scorer):
    LIBRARY_ID = 4
    DESCRIPTION = """Scoring will be as follows:
• Winning Field 1 yields 5 points
• Each field after yields 1 additional point
    • For example, Field 2 yields 6 points
    • Field 3 yields 7...and so on and so forth
• Tying a field yields 0 points
"""

    @classmethod
    def calculate_match_score(
        cls,
        main_submission: list[int],
        other_submission: list[int],
    ) -> float:
        cls.validate_submissions(main_submission, other_submission)
        points = 0
        for i in range(len(main_submission)):
            points += (5 + i) if main_submission[i] - other_submission[i] > 0 else 0

        return points


class IncreasingValueByTwo(Scorer):
    LIBRARY_ID = 5
    DESCRIPTION = """Scoring will be as follows:
• Winning Field 1 yields 5 points
• Each field after yields 1 additional point
    • For example, Field 2 yields 6 points
    • Field 3 yields 7...and so on and so forth
"""

    @classmethod
    def calculate_match_score(
        cls,
        main_submission: list[int],
        other_submission: list[int],
    ) -> float:
        cls.validate_submissions(main_submission, other_submission)
        points = 0
        for i in range(len(main_submission)):
            points += (
                (5 + (2 * i)) if main_submission[i] - other_submission[i] > 0 else 0
            )

        return points


class FlatValueWinOnly(Scorer):
    LIBRARY_ID = 6
    DESCRIPTION = """Scoring will be as follows:
• Winning a field will yield 3 points
• Tying a field or losing will yield 0 points
"""

    @classmethod
    def calculate_match_score(
        cls,
        main_submission: list[int],
        other_submission: list[int],
    ) -> float:
        cls.validate_submissions(main_submission, other_submission)
        points = 0
        for i in range(len(main_submission)):
            points += 3 if main_submission[i] - other_submission[i] > 0 else 0

        return points


class FlatValueTiesAllowed(Scorer):
    LIBRARY_ID = 7
    DESCRIPTION = """Scoring will be as follows:
• Winning a field will yield 4 points
• Tying a field will yield 2 points
• Losing a field will yield 0 points
"""

    @classmethod
    def calculate_match_score(
        cls, main_submission: list[int], other_submission: list[int]
    ) -> float:
        cls.validate_submissions(main_submission, other_submission)
        points = 0
        for i in range(len(main_submission)):
            match difference := main_submission[i] - other_submission[i]:
                case difference if difference > 0:
                    points += 4
                case difference if difference == 0:
                    points += 2

        return points


ScoringLibrary = BlottoLibrary(Scorer)
