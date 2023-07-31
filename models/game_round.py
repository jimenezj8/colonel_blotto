import sqlalchemy as sa
from sqlalchemy import orm

from models.common import Base, CascadeForeignKey


class GameRound(Base):
    __tablename__ = "game_round"

    game_id = orm.mapped_column(CascadeForeignKey("game.id"), nullable=False)
    number = orm.mapped_column(sa.Integer, nullable=False)
    library_id = orm.mapped_column(sa.Integer, nullable=False)
    start = orm.mapped_column(sa.DateTime, nullable=False)
    end = orm.mapped_column(sa.DateTime, nullable=False)
    fields = orm.mapped_column(sa.Integer, nullable=False)
    soldiers = orm.mapped_column(sa.Integer, nullable=False)

    __table_args__ = (
        sa.PrimaryKeyConstraint("game_id", "number", name="game_round_pk"),
    )

    def __repr__(self):
        return (
            "Round("
            f"game_id={self.game_id!r}, "
            f"number={self.round!r}, "
            f"library_id={self.library_id!r}, "
            f"start={self.start!r}, "
            f"end={self.end!r}, "
            f"fields={self.fields!r}, "
            f"soldiers={self.soldiers!r}"
            ")"
        )
