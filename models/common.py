from sqlalchemy import ForeignKey, orm


class Base(orm.DeclarativeBase):
    pass


MetaData = Base.metadata


class CascadeForeignKey(ForeignKey):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, onupdate="CASCADE", ondelete="CASCADE")
