from typing import Iterable

from .meta import SessionMaker


def create_records(records: Iterable[any]):
    with SessionMaker() as session:
        session.expire_on_commit = False  # https://sqlalche.me/e/20/bhk3
        session.add_all(records)
        session.commit()
