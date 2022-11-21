import datetime
import os

import sqlalchemy as sa

import blotto

from models import MetaData


engine = sa.create_engine(os.getenv("BLOTTO_DB"), echo=True)


def signup_exists(user_id, game_id):
    signups = MetaData.tables["signups"]

    select = signups.select().where(
        signups.c.user_id == user_id, signups.c.game_id == game_id
    )

    with engine.connect() as con:
        result = con.execute(select).all()
        if len(result) != 0:
            return True

    return False


def add_user_to_game(user_id, game_id):
    metadata = sa.MetaData(engine)
    metadata.reflect()

    signups = metadata.tables["signups"]

    insert = signups.insert().values(user_id=user_id, game_id=game_id)

    with engine.connect() as con:
        con.execute(insert)


def remove_user_from_game(user_id, game_id):
    metadata = sa.MetaData(engine)
    metadata.reflect()

    signups = metadata.tables["signups"]

    delete = signups.delete().where(
        signups.c.user_id == user_id, signups.c.game_id == game_id
    )

    with engine.connect() as con:
        con.execute(delete)


def create_new_game(
    num_rounds: int, round_length: datetime.timedelta, game_start: datetime.datetime
):
    metadata = sa.MetaData(engine)
    metadata.reflect()

    games = metadata.tables["games"]

    insert = games.insert().values(
        num_rounds=num_rounds,
        round_length=round_length,
        start=game_start,
    )

    with engine.connect() as con:
        result = con.execute(insert)

    return result


# TODO: convert all references to round_length to store datetime.timedelta
def generate_rounds(
    game_id: int,
    num_rounds: int,
    round_length: datetime.timedelta,
    game_start: datetime.datetime,
):
    metadata = sa.MetaData(engine)
    metadata.reflect()

    rounds = metadata.tables["rounds"]

    values = []
    for round_number in range(num_rounds):
        round = blotto.RoundLibrary.get_random()
        row = {
            "id": round.ID,
            "game_id": game_id,
            "number": round_number + 1,
            "start": (game_start + round_length * round_number),
            "end": (game_start + round_length * (round_number + 1)),
        }
        values.append(row)

    insert = rounds.insert().values(values)
    with engine.connect() as con:
        result = con.execute(insert)

    return result


def get_game_start(game_id):
    metadata = sa.MetaData(engine)
    metadata.reflect()

    games = metadata.tables["games"]

    select = games.select().where(games.c.id == game_id)

    with engine.connect() as con:
        result = con.execute(select).first()[-1]

    return result


def get_user_signups(user_id):
    metadata = sa.MetaData(engine)
    metadata.reflect()

    signups = metadata.tables["signups"]

    select = sa.select([signups.c.game_id]).where(signups.c.user_id == user_id)

    participating_in = []
    with engine.connect() as con:
        for row in con.execute(select):
            participating_in.append(row[0])

    return participating_in
