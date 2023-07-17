import sqlalchemy as sa
from meta import SessionMaker

from models import (
    GameRound,
)


def get_game_round(id: int) -> GameRound:
    sql = sa.select(GameRound).where(GameRound.id == id)

    with SessionMaker() as session:
        return session.execute(sql).scalar_one()
