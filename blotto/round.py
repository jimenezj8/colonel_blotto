import logging
from typing import Self

from blotto.deploying import Deployer, DeployingLibrary
from blotto.scoring import Scorer, ScoringLibrary
from blotto.stage import Stage, StageLibrary

logging.basicConfig(level=logging.INFO)


class BlottoRound:
    """Round implementation tying all aspects of Blotto together.

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
        fields: int,
        soldiers: int,
    ):
        """
        If not using an existing BlottoRound or GameRound configuration, create new
        instances using `from_new` instead, which will randomly select the number of
        fields and soldiers for the round, as well as a Stage, Deployer, and Scorer.
        """
        self._stage = stage
        self._deployer = deployer
        self._scorer = scorer

        self._fields = fields
        self._soldiers = soldiers

    @classmethod
    def from_new(cls: type[Self]) -> Self:
        """Returns a BlottoRound with random configuration.

        Uses the subclass-specific algorithm to randomly generate
        a number of fields and soldiers.
        """
        fields = cls._random_fields()
        soldiers = cls._random_soldiers()

        stage = StageLibrary.get_random()
        deployer = DeployingLibrary.get_random()
        scorer = ScoringLibrary.get_random()

        return cls(stage, deployer, scorer, fields, soldiers)

    @property
    def stage(self) -> type[Stage]:
        return self._stage

    @property
    def deployer(self) -> type[Deployer]:
        return self._deployer

    @property
    def scorer(self) -> type[Scorer]:
        return self._scorer

    @property
    def fields(self) -> int:
        return self._fields

    @property
    def soldiers(self) -> int:
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
