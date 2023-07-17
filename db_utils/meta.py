"""
Contains implementations common to all db_utils
"""
from sqlalchemy.orm import sessionmaker

from models import Engine

SessionMaker = sessionmaker(Engine)
