import datetime

import sqlalchemy as sa
from sqlalchemy import orm

from models.common import Base


class Submission(Base):
    __tablename__ = "submission"

    game_id: orm.Mapped[int] = orm.mapped_column(sa.Integer, nullable=False)
    user_id: orm.Mapped[str] = orm.mapped_column(sa.Text, nullable=False)
    round_number: orm.Mapped[int] = orm.mapped_column(sa.Integer, nullable=False)
    field: orm.Mapped[int] = orm.mapped_column(sa.Integer, nullable=False)
    soldiers: orm.Mapped[int] = orm.mapped_column(sa.Integer, nullable=False)
    timestamp: orm.Mapped[datetime.datetime] = orm.mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        sa.ForeignKeyConstraint(
            columns=["game_id", "user_id"],
            refcolumns=["participant.game_id", "participant.user_id"],
        ),
        sa.ForeignKeyConstraint(
            columns=["game_id", "round_number"],
            refcolumns=["game_round.game_id", "game_round.number"],
        ),
        sa.PrimaryKeyConstraint(
            "game_id",
            "user_id",
            "round_number",
            "field",
            "timestamp",
            name="submission_pk",
        ),
    )
