"""
Contains implementations common to all db_utils
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(os.getenv("BLOTTO_DB"), echo=True)

SessionMaker = sessionmaker(engine)
