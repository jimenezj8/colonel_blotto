import os

import sqlalchemy as sa
import sqlalchemy.orm as orm


engine = sa.create_engine(os.getenv("BLOTTO_DB"))
Base = orm.declarative_base(bind=engine)


class Game(Base):
    __tablename__ = "game"

    id = sa.Column(sa.Integer, primary_key=True)
    round_length = sa.Column(sa.Interval, nullable=False)
    num_rounds = sa.Column(sa.Integer, nullable=False)
    start = sa.Column(sa.DateTime(timezone=True), nullable=False)

    def __repr__(self):
        return f"Game(id={self.id!r}, round_length={self.round_length!r}, num_rounds={self.num_rounds!r}, start={self.start!r})"


class Participant(Base):
    __tablename__ = "participant"

    game_id = sa.Column(sa.ForeignKey("game.id", ondelete="CASCADE"), nullable=False)
    user_id = sa.Column(sa.Text, nullable=False)

    sa.PrimaryKeyConstraint(game_id, user_id, name="signup")

    def __repr__(self):
        return f"Participant(user_id={self.user_id!r}, game_id={self.game_id!r})"


class Round(Base):
    __tablename__ = "round"

    id = sa.Column(sa.Integer, nullable=False)
    game_id = sa.Column(sa.ForeignKey("game.id", ondelete="CASCADE"), nullable=False)
    number = sa.Column(sa.Integer, nullable=False)
    start = sa.Column(sa.DateTime, nullable=False)
    end = sa.Column(sa.DateTime, nullable=False)

    __tableargs__ = (
        sa.PrimaryKeyConstraint(game_id, number, name="round_pk"),
        {},
    )

    def __repr__(self):
        return f"Round(id={self.id!r}, game_id={self.game_id!r}, number={self.round!r}, start={self.start!r}, end={self.end!r})"


class Submission(Base):
    __tablename__ = "submission"

    id = sa.Column(sa.Integer, primary_key=True)
    game_id = sa.Column(sa.ForeignKey("games.id", ondelete="CASCADE"), nullable=False)
    user_id = sa.Column(sa.Text, nullable=False)
    round_number = sa.Column(sa.Integer, nullable=False)
    field_number = sa.Column(sa.Integer, nullable=False)
    num_soldiers = sa.Column(sa.Integer, nullable=False)


class Result(Base):
    __tablename__ = "result"

    # TODO: primarykeyconstraint on foreignkey signup from participant table
    game_id = sa.Column(sa.ForeignKey("games.id", ondelete="CASCADE"), primary_key=True)
    user_id = sa.Column(sa.Text, nullable=False)
    round_number = sa.Column(sa.Integer, nullable=False)
    score = sa.Column(sa.Float, nullable=True)
    rank = sa.Column(sa.Integer, nullable=True)


MetaData = Base.metadata
