import sqlalchemy as sa
from sqlalchemy import orm

from models.common import Base, CascadeForeignKey


class Participant(Base):
    __tablename__ = "participant"

    game_id = orm.mapped_column(CascadeForeignKey("game.id"), nullable=False)
    user_id = orm.mapped_column(sa.Text, nullable=False)

    __table_args__ = (
        sa.PrimaryKeyConstraint("game_id", "user_id", name="participant_pk"),
    )

    def __repr__(self):
        return f"Participant(user_id={self.user_id!r}, game_id={self.game_id!r})"
