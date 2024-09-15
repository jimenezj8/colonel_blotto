from blotto.framework.round import BlottoRound


class Game:
    def __init__(self, num_rounds: int):

        self.rounds = [BlottoRound.from_new() for i in range(num_rounds)]
