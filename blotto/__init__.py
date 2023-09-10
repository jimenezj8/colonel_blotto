# ruff: noqa

"""A library for running games of Blotto.

Blotto "is a type of two-person constant-sum game" ([Wikipedia](https://en.wikipedia.org/wiki/Blotto_game)).
In a game of Blotto, multiple battles are fought by players in which they operate using the same constraints:
- Number of battlefields available to fight in
- Number of soldiers to deploy across the battlefields
- Restrictions on how to deploy soldiers across battlefields
- Deployment costs
- Scoring for winning/tying/losing battlefields

Many players can participate in a tournament! For the purposes of this package, the definition of a Game
and a tournament are one and the same. A tournament is a series of battles, or rounds, where players
submit their deployment strategies given a set of constraints.

In a typical game, each submission is compared against every other submission in a battle, and the round
score for a participant is their average score in each battle. When the dust settles at the end of a Game,
the participant with the highest total round score wins!
"""
