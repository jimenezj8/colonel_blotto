import datetime

import pandas as pd
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from models import (
    Engine,
    Game,
    GameResult,
    MetaData,
    Participant,
    Round,
    RoundResult,
    Submission,
)

Session = sessionmaker(Engine)


def check_participation(user_id: str, game_id: int) -> Participant:
    select = sa.select(Participant).where(
        Participant.user_id == user_id, Participant.game_id == game_id
    )

    with Session() as session:
        return session.execute(select).scalar_one()


def add_user_to_game(user_id, game_id):
    signups = MetaData.tables["participant"]

    insert = signups.insert().values(user_id=user_id, game_id=game_id)

    with Engine.connect() as con:
        con.execute(insert)


def remove_user_from_game(user_id, game_id):
    signups = MetaData.tables["participant"]

    delete = signups.delete().where(
        signups.c.user_id == user_id, signups.c.game_id == game_id
    )

    with Engine.connect() as con:
        con.execute(delete)


def create_new_game(
    num_rounds: int, round_length: datetime.timedelta, game_start: datetime.datetime
) -> int:
    insert = sa.insert(Game).values(
        num_rounds=num_rounds,
        round_length=round_length,
        start=game_start,
        canceled=False,
    )

    with Session() as session:
        result = session.execute(insert)
        session.commit()

    return result.inserted_primary_key[0]


def create_new_rounds(rounds: list[dict]) -> None:
    rounds = [Round(**round) for round in rounds]
    with Session() as session:
        session.add_all(rounds)
        session.commit()


def get_game_start(game_id: int) -> datetime.datetime:
    select = sa.select(Game.start).where(Game.id == game_id)

    with Session() as session:
        return session.execute(select).first()[0]


def get_user_active_games(user_id: str) -> list[Game]:
    select = (
        sa.select(Game)
        .join(Participant, Game.id == Participant.game_id)
        .where(Participant.user_id == user_id)
    )

    with Session() as session:
        return session.execute(select).scalars().all()


def get_round(game_id: int, round_num: int) -> Round | None:
    select = sa.select(Round).where(Round.game_id == game_id, Round.number == round_num)

    with Session() as session:
        return session.execute(select).scalars().first()


def get_round_length(game_id: int) -> datetime.timedelta:
    select = sa.select(Game.round_length).where(Game.id == game_id)

    with Session() as session:
        return session.execute(select).scalar_one()


def cancel_game(game_id: int) -> None:
    update = sa.update(Game).where(Game.id == game_id).values(canceled=True)

    with Session() as session:
        session.execute(update)

    cancel_rounds(game_id)


def cancel_rounds(game_id: int) -> None:
    update = sa.update(Round).where(Round.game_id == game_id).values(canceled=True)

    with Session() as session:
        session.execute(update)


def get_participants(game_id: int) -> list:
    select = sa.select(Participant).where(Participant.game_id == game_id)

    with Session() as session:
        return session.execute(select).scalars().all()


def get_game(game_id: int) -> Game:
    select = sa.select(Game).where(Game.id == game_id)

    with Session() as session:
        return session.execute(select).scalar_one()


def get_round_results(game_id: int, round_num: int) -> list[RoundResult]:
    select = (
        sa.select(RoundResult)
        .where(RoundResult.game_id == game_id, RoundResult.round_number == round_num)
        .order_by(RoundResult.rank.asc())
    )

    with Session() as session:
        return session.execute(select).scalars().all()


def get_game_results(game_id: int) -> list[GameResult]:
    select = (
        sa.select(GameResult)
        .where(GameResult.game_id == game_id)
        .order_by(GameResult.rank.asc())
    )

    with Session() as session:
        return session.execute(select).scalars().all()


def get_submissions_dataframe(game_id: int) -> pd.DataFrame:
    select = sa.select(Submission).where(Submission.game_id == game_id)

    return pd.read_sql(str(select), Engine)


def get_round_results_dataframe(game_id: int) -> pd.DataFrame:
    select = sa.select(RoundResult).where(RoundResult.game_id == game_id)

    return pd.read_sql(str(select), Engine)


def get_active_round(game_id: int, current_time: datetime.datetime) -> Round:
    select = sa.select(Round).where(
        Round.game_id == game_id, Round.start < current_time, Round.end > current_time
    )

    with Session() as session:
        return session.execute(select).scalar_one()


def submit_user_strategy(
    game_id: int,
    round_num: int,
    user_id: str,
    strategy: list[int],
    timestamp: datetime.datetime,
) -> None:
    submissions = [
        Submission(
            game_id=game_id,
            user_id=user_id,
            round_number=round_num,
            field=i + 1,
            soldiers=soldiers,
            timestamp=timestamp,
        )
        for i, soldiers in enumerate(strategy)
    ]

    with Session() as session:
        session.add_all(submissions)
        session.commit()
