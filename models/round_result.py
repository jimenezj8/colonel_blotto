import sqlalchemy as sa
from sqlalchemy import orm

from models.common import Base


class RoundResult(Base):
    __tablename__ = "round_result"

    game_id: orm.Mapped[int] = orm.mapped_column(sa.Integer, nullable=False)
    user_id: orm.Mapped[str] = orm.mapped_column(sa.Text, nullable=False)
    round_number: orm.Mapped[int] = orm.mapped_column(sa.Integer, nullable=False)
    score: orm.Mapped[float] = orm.mapped_column(sa.Float, nullable=True)
    rank: orm.Mapped[int] = orm.mapped_column(sa.Integer, nullable=True)

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
            "game_id", "user_id", "round_number", name="round_result_pk"
        ),
    )
