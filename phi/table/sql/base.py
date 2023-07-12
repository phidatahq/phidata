try:
    from sqlalchemy.orm import DeclarativeBase
except ImportError:
    raise ImportError("`sqlalchemy` not installed")


class BaseTable(DeclarativeBase):
    """
    Base class for SQLAlchemy model definitions.

    https://docs.sqlalchemy.org/en/20/orm/mapping_api.html#sqlalchemy.orm.DeclarativeBase
    https://fastapi.tiangolo.com/tutorial/sql-databases/#create-a-base-class
    """

    pass
