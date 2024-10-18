from typing import Optional, List
from sqlalchemy import create_engine, MetaData, Table, Column, String, DateTime, text, select, delete, inspect
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError

from phi.memory.db import MemoryDb
from phi.memory.row import MemoryRow
from phi.utils.log import logger


class SqliteMemoryDb(MemoryDb):
    def __init__(
        self,
        table_name: str = "memory",
        db_path: str = "memory.db",
    ):
        """
        This class provides a memory store backed by a SQLite table using SQLAlchemy.

        Args:
            table_name (str): The name of the table to store memory rows.
            db_path (str): The path to the SQLite database file. Defaults to ':memory:' for in-memory database.
        """
        self.table_name: str = table_name
        self.db_path: str = db_path
        self.engine = create_engine(f"sqlite:///{self.db_path}")
        self.inspector = inspect(self.engine)
        self.metadata = MetaData()
        self.Session = scoped_session(sessionmaker(bind=self.engine))
        self.table = self.get_table()
        self.create()

    def get_table(self) -> Table:
        return Table(
            self.table_name,
            self.metadata,
            Column("id", String, primary_key=True),
            Column("user_id", String),
            Column("memory", String),
            Column("created_at", DateTime, server_default=text("CURRENT_TIMESTAMP")),
            Column(
                "updated_at", DateTime, server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP")
            ),
            extend_existing=True,
        )

    def create(self) -> None:
        if not self.table_exists():
            try:
                logger.debug(f"Creating table: {self.table_name}")
                self.metadata.create_all(self.engine)
            except SQLAlchemyError as e:
                logger.error(f"Error creating table '{self.table_name}': {e}")
                raise

    def memory_exists(self, memory: MemoryRow) -> bool:
        with self.Session() as session:
            stmt = select(self.table.c.id).where(self.table.c.id == memory.id)
            result = session.execute(stmt).first()
            return result is not None

    def read_memories(
        self, user_id: Optional[str] = None, limit: Optional[int] = None, sort: Optional[str] = None
    ) -> List[MemoryRow]:
        memories: List[MemoryRow] = []
        try:
            with self.Session() as session:
                stmt = select(self.table)
                if user_id is not None:
                    stmt = stmt.where(self.table.c.user_id == user_id)

                if sort == "asc":
                    stmt = stmt.order_by(self.table.c.created_at.asc())
                else:
                    stmt = stmt.order_by(self.table.c.created_at.desc())

                if limit is not None:
                    stmt = stmt.limit(limit)

                result = session.execute(stmt)
                for row in result:
                    memories.append(MemoryRow(id=row.id, user_id=row.user_id, memory=eval(row.memory)))
        except SQLAlchemyError as e:
            logger.debug(f"Exception reading from table: {e}")
            logger.debug(f"Table does not exist: {self.table_name}")
            logger.debug("Creating table for future transactions")
            self.create()
        return memories

    def upsert_memory(self, memory: MemoryRow, create_and_retry: bool = True) -> None:
        try:
            with self.Session() as session:
                # Check if the memory already exists
                existing = session.execute(select(self.table).where(self.table.c.id == memory.id)).first()

                if existing:
                    # Update existing memory
                    stmt = (
                        self.table.update()
                        .where(self.table.c.id == memory.id)
                        .values(user_id=memory.user_id, memory=str(memory.memory), updated_at=text("CURRENT_TIMESTAMP"))
                    )
                else:
                    # Insert new memory
                    stmt = self.table.insert().values(id=memory.id, user_id=memory.user_id, memory=str(memory.memory))

                session.execute(stmt)
                session.commit()
        except SQLAlchemyError as e:
            logger.error(f"Exception upserting into table: {e}")
            if not self.table_exists():
                logger.info(f"Table does not exist: {self.table_name}")
                logger.info("Creating table for future transactions")
                self.create()
                if create_and_retry:
                    return self.upsert_memory(memory, create_and_retry=False)
            else:
                raise

    def delete_memory(self, id: str) -> None:
        with self.Session() as session:
            stmt = delete(self.table).where(self.table.c.id == id)
            session.execute(stmt)
            session.commit()

    def drop_table(self) -> None:
        if self.table_exists():
            logger.debug(f"Deleting table: {self.table_name}")
            self.table.drop(self.engine)

    def table_exists(self) -> bool:
        return self.inspector.has_table(self.table_name)

    def clear(self) -> bool:
        with self.Session() as session:
            stmt = delete(self.table)
            session.execute(stmt)
            session.commit()
        return True

    def __del__(self):
        self.Session.remove()
