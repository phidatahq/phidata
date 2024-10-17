from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Base class for SQLAlchemy model definitions.

    https://fastapi.tiangolo.com/tutorial/sql-databases/#create-a-base-class
    https://docs.sqlalchemy.org/en/20/orm/mapping_api.html#sqlalchemy.orm.DeclarativeBase
    """

    metadata = MetaData(schema="public")
