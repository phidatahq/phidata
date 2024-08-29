from typing import Optional, Any, List

try:
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.engine import create_engine, Engine
    from sqlalchemy.engine.row import Row
    from sqlalchemy.inspection import inspect
    from sqlalchemy.orm import Session, sessionmaker
    from sqlalchemy.schema import MetaData, Table, Column
    from sqlalchemy.sql.expression import text, select
    from sqlalchemy.types import DateTime, String
except ImportError:
    raise ImportError("`sqlalchemy` not installed")

from phi.assistant.thread import AssistantThread
from phi.storage.assistant.base import AssistantStorage
from phi.utils.log import logger


class PgAssistantStorage(AssistantStorage):
    def __init__(
        self,
        table_name: str,
        schema: Optional[str] = "ai",
        db_url: Optional[str] = None,
        db_engine: Optional[Engine] = None,
    ):
        """
        This class provides assistant storage using a postgres table.

        The following order is used to determine the database connection:
            1. Use the db_engine if provided
            2. Use the db_url

        :param table_name: The name of the table to store assistant runs.
        :param schema: The schema to store the table in.
        :param db_url: The database URL to connect to.
        :param db_engine: The database engine to use.
        """
        _engine: Optional[Engine] = db_engine
        if _engine is None and db_url is not None:
            _engine = create_engine(db_url)

        if _engine is None:
            raise ValueError("Must provide either db_url or db_engine")

        # Database attributes
        self.table_name: str = table_name
        self.schema: Optional[str] = schema
        self.db_url: Optional[str] = db_url
        self.db_engine: Engine = _engine
        self.metadata: MetaData = MetaData(schema=self.schema)

        # Database session
        self.Session: sessionmaker[Session] = sessionmaker(bind=self.db_engine)

        # Database table for storage
        self.table: Table = self.get_table()

    def get_table(self) -> Table:
        return Table(
            self.table_name,
            self.metadata,
            # Primary key for this run
            Column("thread_id", String, primary_key=True),
            # ID of the user participating in this run
            Column("user_id", String),
            # -*- LLM data (name, model, etc.)
            Column("llm", postgresql.JSONB),
            # -*- Assistant memory
            Column("memory", postgresql.JSONB),
            # Metadata associated with this assistant
            Column("assistant_data", postgresql.JSONB),
            # Metadata associated with this run
            Column("thread_data", postgresql.JSONB),
            # Metadata associated the user participating in this run
            Column("user_data", postgresql.JSONB),
            # The timestamp of when this run was created.
            Column("created_at", DateTime(timezone=True), server_default=text("now()")),
            # The timestamp of when this run was last updated.
            Column("updated_at", DateTime(timezone=True), onupdate=text("now()")),
            extend_existing=True,
        )

    def table_exists(self) -> bool:
        logger.debug(f"Checking if table exists: {self.table.name}")
        try:
            return inspect(self.db_engine).has_table(self.table.name, schema=self.schema)
        except Exception as e:
            logger.error(e)
            return False

    def create(self) -> None:
        if not self.table_exists():
            if self.schema is not None:
                with self.Session() as sess, sess.begin():
                    logger.debug(f"Creating schema: {self.schema}")
                    sess.execute(text(f"create schema if not exists {self.schema};"))
            logger.debug(f"Creating table: {self.table_name}")
            self.table.create(self.db_engine)

    def _read(self, session: Session, thread_id: str) -> Optional[Row[Any]]:
        stmt = select(self.table).where(self.table.c.thread_id == thread_id)
        try:
            return session.execute(stmt).first()
        except Exception:
            # Create table if it does not exist
            self.create()
        return None

    def read(self, thread_id: str) -> Optional[AssistantThread]:
        with self.Session() as sess, sess.begin():
            existing_row: Optional[Row[Any]] = self._read(session=sess, thread_id=thread_id)
            try:
                return AssistantThread.model_validate(existing_row) if existing_row is not None else None
            except Exception:
                logger.error(f"Error reading run: {thread_id}")
                # MIGRATE
                # if an automatic migration is possible, great
                # otherwise, throw and error pointing to the documentaion and support channel

    def get_all_thread_ids(self, user_id: Optional[str] = None) -> List[str]:
        thread_ids: List[str] = []
        try:
            with self.Session() as sess, sess.begin():
                # get all thread_ids for this user
                stmt = select(self.table)
                if user_id is not None:
                    stmt = stmt.where(self.table.c.user_id == user_id)
                # order by created_at desc
                stmt = stmt.order_by(self.table.c.created_at.desc())
                # execute query
                rows = sess.execute(stmt).fetchall()
                for row in rows:
                    if row is not None and row.thread_id is not None:
                        thread_ids.append(row.thread_id)
        except Exception:
            logger.debug(f"Table does not exist: {self.table.name}")
        return thread_ids

    def get_all_threads(self, user_id: Optional[str] = None) -> List[AssistantThread]:
        runs: List[AssistantThread] = []
        try:
            with self.Session() as sess, sess.begin():
                # get all runs for this user
                stmt = select(self.table)
                if user_id is not None:
                    stmt = stmt.where(self.table.c.user_id == user_id)
                # order by created_at desc
                stmt = stmt.order_by(self.table.c.created_at.desc())
                # execute query
                rows = sess.execute(stmt).fetchall()
                for row in rows:
                    if row.thread_id is not None:
                        runs.append(AssistantThread.model_validate(row))
        except Exception:
            logger.debug(f"Table does not exist: {self.table.name}")
        return runs

    def upsert(self, row: AssistantThread) -> Optional[AssistantThread]:
        """
        Create a new assistant run if it does not exist, otherwise update the existing assistant.
        """

        with self.Session() as sess, sess.begin():
            # Create an insert statement
            stmt = postgresql.insert(self.table).values(
                thread_id=row.thread_id,
                user_id=row.user_id,
                llm=row.llm,
                memory=row.memory,
                assistant_data=row.assistant_data,
                thread_data=row.thread_data,
                user_data=row.user_data,
            )

            # Define the upsert if the thread_id already exists
            # See: https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#postgresql-insert-on-conflict
            stmt = stmt.on_conflict_do_update(
                index_elements=["thread_id"],
                set_=dict(
                    user_id=row.user_id,
                    llm=row.llm,
                    memory=row.memory,
                    assistant_data=row.assistant_data,
                    thread_data=row.thread_data,
                    user_data=row.user_data,
                ),  # The updated value for each column
            )

            try:
                sess.execute(stmt)
            except Exception:
                # Create table and try again
                self.create()
                sess.execute(stmt)
        return self.read(thread_id=row.thread_id)

    def delete(self) -> None:
        if self.table_exists():
            logger.debug(f"Deleting table: {self.table_name}")
            self.table.drop(self.db_engine)
