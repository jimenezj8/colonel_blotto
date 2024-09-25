import logging
from typing import Self

from blotto.core.deploying import Deployer, DeployingLibrary
from blotto.core.library import BlottoLibrary
from blotto.core.scoring import Scorer, ScoringLibrary
from blotto.core.stage import Stage, StageLibrary

logging.basicConfig(level=logging.INFO)


class BlottoRound:
    """Round implementation tying all components of Blotto together.

    BlottoRound is the application-driving metaclass for rounds. This metaclass
    defines what each new type of round must be able to do and what characteristics
    must be provided. A BlottoRound cannot exist without at least a number of
    fields and soldiers, a stage, a deployer, and a scorer.

    Attributes:
    - STAGE_ID (int): the StageLibrary ID of the Stage
    - DEPLOYER_ID (int): the DeployerLibrary ID of the Deployer
    - SCORER_ID (int): the ScorerLibrary ID of the Scorer
    - fields (int): the number of fields in a BlottoRound instance
    - soldiers (int): the number of soliders in a BlottoRound instance
    """

    def __init__(
        self,
        stage: type[Stage],
        deployer: type[Deployer],
        scorer: type[Scorer],
    ):
        """
        If not using an existing BlottoRound or GameRound configuration, create new
        instances using `from_new` instead, which will randomly select a Stage,
        Deployer, and Scorer.
        """
        self._stage = stage
        self._deployer = deployer
        self._scorer = scorer

    @classmethod
    def from_new(cls: type[Self]) -> Self:
        """Returns a BlottoRound with random configuration.

        Uses the subclass-specific algorithm to randomly generate
        a number of fields and soldiers.
        """
        stage = StageLibrary.get_random()
        deployer = DeployingLibrary.get_random()
        scorer = ScoringLibrary.get_random()

        return cls(stage, deployer, scorer)

    @property
    def stage(self) -> Stage:
        return self._stage

    @property
    def deployer(self) -> type[Deployer]:
        return self._deployer

    @property
    def scorer(self) -> type[Scorer]:
        return self._scorer


RoundLibrary = BlottoLibrary(BlottoRound)
