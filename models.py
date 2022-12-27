import os

import sqlalchemy as sa
import sqlalchemy.orm as orm

Engine = sa.create_engine(os.getenv("BLOTTO_DB"))
Base = orm.declarative_base(bind=Engine)


class Game(Base):
    __tablename__ = "game"

    id = sa.Column(sa.Integer, primary_key=True)
    round_length = sa.Column(sa.Interval, nullable=False)
    num_rounds = sa.Column(sa.Integer, nullable=False)
    start = sa.Column(sa.DateTime(timezone=True), nullable=False)
    canceled = sa.Column(sa.Boolean, nullable=False)

    def __repr__(self):
        return f"Game(id={self.id!r}, round_length={self.round_length!r}, num_rounds={self.num_rounds!r}, start={self.start!r})"


class Participant(Base):
    __tablename__ = "participant"

    game_id = sa.Column(sa.ForeignKey("game.id"), nullable=False)
    user_id = sa.Column(sa.Text, nullable=False)

    __table_args__ = (
        sa.PrimaryKeyConstraint("game_id", "user_id", name="participant_pk"),
        {},
    )

    def __repr__(self):
        return f"Participant(user_id={self.user_id!r}, game_id={self.game_id!r})"


class Round(Base):
    __tablename__ = "round"

    id = sa.Column(sa.Integer, nullable=False)
    game_id = sa.Column(sa.ForeignKey("game.id"), nullable=False)
    number = sa.Column(sa.Integer, nullable=False)
    start = sa.Column(sa.DateTime, nullable=False)
    end = sa.Column(sa.DateTime, nullable=False)
    fields = sa.Column(sa.Integer, nullable=False)
    soldiers = sa.Column(sa.Integer, nullable=False)
    canceled = sa.Column(sa.Boolean, nullable=False)

    __table_args__ = (
        sa.PrimaryKeyConstraint("game_id", "number", name="round_pk"),
        {},
    )

    def __repr__(self):
        return f"Round(id={self.id!r}, game_id={self.game_id!r}, number={self.round!r}, start={self.start!r}, end={self.end!r})"


class Submission(Base):
    __tablename__ = "submission"

    game_id = sa.Column(nullable=False)
    round_number = sa.Column(nullable=False)
    user_id = sa.Column(nullable=False)
    field_number = sa.Column(sa.Integer, nullable=False)
    num_soldiers = sa.Column(sa.Integer, nullable=False)

    __table_args__ = (
        sa.PrimaryKeyConstraint(
            "game_id", "round_number", "user_id", "field_number", name="submission_pk"
        ),
        sa.ForeignKeyConstraint(
            columns=["game_id", "user_id"],
            refcolumns=["participant.game_id", "participant.user_id"],
        ),
        sa.ForeignKeyConstraint(
            columns=["game_id", "round_number"],
            refcolumns=["round.game_id", "round.number"],
        ),
    )


class RoundResult(Base):
    __tablename__ = "round_result"

    game_id = sa.Column(sa.ForeignKey("game.id"))
    user_id = sa.Column(sa.Text, nullable=False)
    round_number = sa.Column(sa.Integer, nullable=False)
    score = sa.Column(sa.Float, nullable=True)
    rank = sa.Column(sa.Integer, nullable=True)

    __table_args__ = (
        sa.PrimaryKeyConstraint("game_id", "round_number", name="roundresult_pk"),
        {},
    )


class GameResult(Base):
    __tablename__ = "game_result"

    game_id = sa.Column(nullable=False)
    user_id = sa.Column(nullable=False)
    score = sa.Column(sa.Float, nullable=False)
    rank = sa.Column(sa.Integer, nullable=False)

    __table_args__ = (
        sa.PrimaryKeyConstraint("game_id", "user_id", name="gameresult_pk"),
        sa.ForeignKeyConstraint(
            columns=["game_id", "user_id"],
            refcolumns=["participant.game_id", "participant.user_id"],
        ),
    )


MetaData = Base.metadata
