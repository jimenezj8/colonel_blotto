from typing import Iterable

from .meta import SessionMaker


def create_records(records: Iterable[any]):
    with SessionMaker() as session:
        session.expire_on_commit = False  # https://sqlalche.me/e/20/bhk3
        session.add_all(records)
        session.commit()


def update_records(records: Iterable[any]):
    create_records(records)


def delete_records(records: Iterable[any]):
    with SessionMaker() as session:
        for record in records:
            session.delete(record)
        session.commit()
