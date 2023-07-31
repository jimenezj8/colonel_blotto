import sqlalchemy as sa
from sqlalchemy import orm

from models.common import Base


class GameResult(Base):
    __tablename__ = "game_result"

    game_id = orm.mapped_column(sa.Integer, nullable=False)
    user_id = orm.mapped_column(sa.Text, nullable=False)
    score = orm.mapped_column(sa.Float, nullable=False)
    rank = orm.mapped_column(sa.Integer, nullable=False)

    __table_args__ = (
        sa.PrimaryKeyConstraint("game_id", "user_id", name="gameresult_pk"),
        sa.ForeignKeyConstraint(
            columns=["game_id", "user_id"],
            refcolumns=["participant.game_id", "participant.user_id"],
        ),
    )
