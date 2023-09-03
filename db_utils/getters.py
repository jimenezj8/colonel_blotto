import datetime
from typing import Sequence

import sqlalchemy as sa

from models import (
    Game,
    GameRound,
    Participant,
)

from .meta import SessionMaker


def get_game_round(game_id: int, number: int) -> GameRound:
    sql = sa.select(GameRound).where(
        GameRound.game_id == game_id, GameRound.number == number
    )

    with SessionMaker() as session:
        return session.execute(sql).scalar_one_or_none()


def get_active_round(game_id: int) -> GameRound:
    sql = sa.select(GameRound).where(
        GameRound.game_id == game_id,
        GameRound.start < datetime.datetime.utcnow(),
        GameRound.end > datetime.datetime.utcnow(),
    )

    with SessionMaker() as session:
        round = session.execute(sql).scalar_one_or_none()

    return round


def get_user_active_games(user_id: str) -> list[Game]:
    "Fetches all active games that the user is signed up for"
    now = datetime.datetime.utcnow()

    select = (
        sa.select(Game)
        .join(Participant)
        .where(
            Participant.user_id == user_id,
            Game.start <= now,
            Game.end >= now,
        )
    )

    with SessionMaker() as session:
        return session.execute(select).scalars().all()


def get_announcement_game(channel: str, ts: datetime.datetime):
    "Fetches a Game record by using the announcement message metadata."
    select = sa.select(Game).where(
        Game.announcement_channel == channel,
        Game.announcement_ts == ts,
    )

    with SessionMaker() as session:
        return session.execute(select).scalar_one()


def get_admin_games(user_id: str) -> Sequence[Game]:
    "Fetches Game records where the indicated user is serving as an admin."
    select = sa.select(Game).where(Game.admin == user_id)

    with SessionMaker() as session:
        return session.execute(select).scalars().all()


def get_game(game_id: int) -> Game:
    "Fetches a single Game by ID"
    select = sa.select(Game).where(Game.id == game_id)

    with SessionMaker() as session:
        return session.execute(select).scalar_one()
