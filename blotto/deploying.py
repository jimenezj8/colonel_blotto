from blotto.library import BlottoLibrary


class Deployer:
    "Deployer manages the costs of sending soldiers to fields."

    @classmethod
    def get_submission_cost(cls, submission: list[int]) -> float:
        "Returns the point cost of deployments in a submission as a positive value."
        raise NotImplementedError


class PerFieldCost(Deployer):
    DESCRIPTION = "Deploying any amount of soldiers to a field costs points."


class PerSoldierCost(Deployer):
    DESCRIPTION = "Deploying a soldier has an associated cost in points."


class ExponentialSoldierCost(PerSoldierCost):
    DESCRIPTION = "Deploying soldiers has an exponentially increasing cost."


class LinearSoldierCost(PerSoldierCost):
    DESCRIPTION = "Deploying soldiers has a linearly increasing cost."


DeployingLibrary = BlottoLibrary(Deployer.__subclasses__())
