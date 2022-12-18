import datetime
import os

import sqlalchemy as sa

from sqlalchemy.orm import Session

import blotto

from models import Engine, MetaData, Game, Participant, Round, Submission, Result


def signup_exists(user_id, game_id):
    signups = MetaData.tables["participant"]

    select = signups.select().where(
        signups.c.user_id == user_id, signups.c.game_id == game_id
    )

    with Engine.connect() as con:
        result = con.execute(select).all()
        if len(result) != 0:
            return True

    return False


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
):
    games = MetaData.tables["game"]

    insert = games.insert().values(
        num_rounds=num_rounds,
        round_length=round_length,
        start=game_start,
    )

    with Engine.connect() as con:
        result = con.execute(insert)

    return result


def generate_rounds(
    game_id: int,
    num_rounds: int,
    round_length: datetime.timedelta,
    game_start: datetime.datetime,
):
    rounds = MetaData.tables["round"]

    values = []
    for round_number in range(num_rounds):
        round = blotto.RoundLibrary.get_random()
        row = {
            "id": round.ID,
            "game_id": game_id,
            "number": round_number + 1,
            "start": (game_start + round_length * round_number),
            "end": (game_start + round_length * (round_number + 1)),
            "fields": round.fields,
            "soldiers": round.soldiers,
        }
        values.append(row)

    insert = rounds.insert().values(values)
    with Engine.connect() as con:
        result = con.execute(insert)

    return result


def get_game_start(game_id: int) -> datetime.datetime:
    select = sa.select(Game.start).where(Game.id == game_id)

    with Session(Engine) as session:
        return session.execute(select).first()[0]


def get_user_signups(user_id):
    signups = MetaData.tables["participant"]

    select = sa.select([signups.c.game_id]).where(signups.c.user_id == user_id)

    participating_in = []
    with Engine.connect() as con:
        for row in con.execute(select):
            participating_in.append(row[0])

    return participating_in


def get_round(game_id: int, round_num: int):
    select = sa.select(Round.id, Round.fields, Round.soldiers).where(
        Round.game_id == game_id, Round.number == round_num
    )

    with Session(Engine) as session:
        return session.execute(select).first()
