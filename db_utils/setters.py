from typing import Iterable

from .meta import SessionMaker


def create_records(records: Iterable[any]):
    with SessionMaker() as session:
        session.add_all(records)
        session.commit()
