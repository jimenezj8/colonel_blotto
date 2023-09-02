import datetime

import sqlalchemy as sa
from sqlalchemy import orm

from models.common import Base


class Game(Base):
    __tablename__ = "game"

    id: orm.Mapped[int] = orm.mapped_column(sa.Integer, primary_key=True)
    admin: orm.Mapped[str] = orm.mapped_column(sa.Text, nullable=False)
    start: orm.Mapped[datetime.datetime] = orm.mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    end: orm.Mapped[datetime.datetime] = orm.mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    num_rounds: orm.Mapped[int] = orm.mapped_column(sa.Integer, nullable=False)
    round_length: orm.Mapped[datetime.timedelta] = orm.mapped_column(
        sa.Interval, nullable=False
    )
    announcement_channel: orm.Mapped[str] = orm.mapped_column(sa.Text, nullable=True)
    announcement_ts: orm.Mapped[datetime.datetime] = orm.mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    canceled: orm.Mapped[bool] = orm.mapped_column(
        sa.Boolean, nullable=False, default=False
    )

    def __repr__(self):
        return (
            "Game("
            f"id={self.id!r}, "
            f"admin={self.admin!r}, "
            f"start={self.start!r}, "
            f"end={self.end!r}, "
            f"num_rounds={self.num_rounds!r}, "
            f"round_length={self.round_length!r}"
            ")"
        )
