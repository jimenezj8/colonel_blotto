import sqlalchemy as sa
from sqlalchemy import orm

from models.common import Base


class Game(Base):
    __tablename__ = "game"

    id = orm.mapped_column(sa.Integer, primary_key=True)
    start = orm.mapped_column(sa.DateTime(timezone=True), nullable=False)
    end = orm.mapped_column(sa.DateTime(timezone=True), nullable=False)
    num_rounds = orm.mapped_column(sa.Integer, nullable=False)
    round_length = orm.mapped_column(sa.Interval, nullable=False)
    announcement_channel = orm.mapped_column(sa.Text, nullable=True)
    announcement_ts = orm.mapped_column(sa.DateTime(timezone=True), nullable=True)
    canceled = orm.mapped_column(sa.Boolean, nullable=False, default=False)

    def __repr__(self):
        return (
            "Game("
            f"id={self.id!r}, "
            f"start={self.start!r}, "
            f"end={self.end!r}, "
            f"num_rounds={self.num_rounds!r}, "
            f"round_length={self.round_length!r}"
            ")"
        )
