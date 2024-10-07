from typing import Optional, Any, List

try:
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.engine import create_engine, Engine
    from sqlalchemy.engine.row import Row
    from sqlalchemy.inspection import inspect
    from sqlalchemy.orm import Session, sessionmaker
    from sqlalchemy.schema import MetaData, Table, Column
    from sqlalchemy.sql.expression import text, select
    from sqlalchemy.types import String, BigInteger
except ImportError:
    raise ImportError("`sqlalchemy` not installed")

from phi.agent.session import AgentSession
from phi.storage.agent.base import AgentStorage
from phi.utils.log import logger


class PgAgentStorage(AgentStorage):
    def __init__(
        self,
        table_name: str,
        schema: Optional[str] = "ai",
        db_url: Optional[str] = None,
        db_engine: Optional[Engine] = None,
        schema_version: int = 1,
        auto_upgrade_schema: bool = False,
    ):
        """
        This class provides Agent storage using a postgres table.

        The following order is used to determine the database connection:
            1. Use the db_engine if provided
            2. Use the db_url

        Args:
            table_name: The name of the table to store Agent sessions.
            schema: The schema to store the table in.
            db_url: The database URL to connect to.
            db_engine: The database engine to use.
            schema_version: The version of the schema.
            auto_upgrade_schema: If True, automatically upgrade the schema.
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

        # Table schema version
        self.schema_version: int = schema_version
        # Automatically upgrade schema if True
        self.auto_upgrade_schema: bool = auto_upgrade_schema

        # Database session
        self.Session: sessionmaker[Session] = sessionmaker(bind=self.db_engine)
        # Database table for storage
        self.table: Table = self.get_table()

    def get_table_v1(self) -> Table:
        return Table(
            self.table_name,
            self.metadata,
            # Session UUID: Primary Key
            Column("session_id", String, primary_key=True),
            # ID of the agent that this session is associated with
            Column("agent_id", String),
            # ID of the user interacting with this agent
            Column("user_id", String),
            # Agent Memory
            Column("memory", postgresql.JSONB),
            # Agent Metadata
            Column("agent_data", postgresql.JSONB),
            # User Metadata
            Column("user_data", postgresql.JSONB),
            # Session Metadata
            Column("session_data", postgresql.JSONB),
            # The Unix timestamp of when this session was created.
            Column("created_at", BigInteger, server_default=text("(extract(epoch from now()))::bigint")),
            # The Unix timestamp of when this session was last updated.
            Column("updated_at", BigInteger, server_onupdate=text("(extract(epoch from now()))::bigint")),
            extend_existing=True,
        )

    def get_table(self) -> Table:
        if self.schema_version == 1:
            return self.get_table_v1()
        else:
            raise ValueError(f"Unsupported schema version: {self.schema_version}")

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

    def _read(self, session: Session, session_id: str) -> Optional[Row[Any]]:
        stmt = select(self.table).where(self.table.c.session_id == session_id)
        try:
            return session.execute(stmt).first()
        except Exception as e:
            logger.debug(f"Exception reading from table: {e}")
            logger.debug(f"Table does not exist: {self.table.name}")
            logger.debug(f"Creating table: {self.table_name}")
            # Create table if it does not exist
            self.create()
        return None

    def read(self, session_id: str) -> Optional[AgentSession]:
        with self.Session() as sess, sess.begin():
            existing_row: Optional[Row[Any]] = self._read(session=sess, session_id=session_id)
            return AgentSession.model_validate(existing_row) if existing_row is not None else None

    def get_all_session_ids(self, user_id: Optional[str] = None, agent_id: Optional[str] = None) -> List[str]:
        session_ids: List[str] = []
        try:
            with self.Session() as sess, sess.begin():
                # get all session_ids for this user
                stmt = select(self.table)
                if user_id is not None:
                    stmt = stmt.where(self.table.c.user_id == user_id)
                if agent_id is not None:
                    stmt = stmt.where(self.table.c.agent_id == agent_id)
                # order by created_at desc
                stmt = stmt.order_by(self.table.c.created_at.desc())
                # execute query
                rows = sess.execute(stmt).fetchall()
                for row in rows:
                    if row is not None and row.session_id is not None:
                        session_ids.append(row.session_id)
        except Exception as e:
            logger.debug(f"Exception reading from table: {e}")
            logger.debug(f"Table does not exist: {self.table.name}")
        return session_ids

    def get_all_sessions(self, user_id: Optional[str] = None, agent_id: Optional[str] = None) -> List[AgentSession]:
        sessions: List[AgentSession] = []
        try:
            with self.Session() as sess, sess.begin():
                # get all sessions for this user
                stmt = select(self.table)
                if user_id is not None:
                    stmt = stmt.where(self.table.c.user_id == user_id)
                if agent_id is not None:
                    stmt = stmt.where(self.table.c.agent_id == agent_id)
                # order by created_at desc
                stmt = stmt.order_by(self.table.c.created_at.desc())
                # execute query
                rows = sess.execute(stmt).fetchall()
                for row in rows:
                    if row.session_id is not None:
                        sessions.append(AgentSession.model_validate(row))
        except Exception as e:
            logger.debug(f"Exception reading from table: {e}")
            logger.debug(f"Table does not exist: {self.table.name}")
        return sessions

    def upsert(self, session: AgentSession) -> Optional[AgentSession]:
        """Create a new AgentSession if it does not exist, otherwise update the existing AgentSession."""

        with self.Session() as sess, sess.begin():
            # Create an insert statement
            stmt = postgresql.insert(self.table).values(
                session_id=session.session_id,
                agent_id=session.agent_id,
                user_id=session.user_id,
                memory=session.memory,
                agent_data=session.agent_data,
                user_data=session.user_data,
                session_data=session.session_data,
            )

            # Define the upsert if the session_id already exists
            # See: https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#postgresql-insert-on-conflict
            stmt = stmt.on_conflict_do_update(
                index_elements=["session_id"],
                set_=dict(
                    agent_id=session.agent_id,
                    user_id=session.user_id,
                    memory=session.memory,
                    agent_data=session.agent_data,
                    user_data=session.user_data,
                    session_data=session.session_data,
                ),  # The updated value for each column
            )

            try:
                sess.execute(stmt)
            except Exception as e:
                logger.debug(f"Exception upserting into table: {e}")
                # Create table and try again
                self.create()
                sess.execute(stmt)
        return self.read(session_id=session.session_id)

    def delete_session(self, session_id: Optional[str] = None):
        if session_id is None:
            logger.warning("No session_id provided for deletion.")
            return

        with self.Session() as sess, sess.begin():
            try:
                # Delete the session with the given session_id
                delete_stmt = self.table.delete().where(self.table.c.session_id == session_id)
                result = sess.execute(delete_stmt)

                if result.rowcount == 0:
                    logger.warning(f"No session found with session_id: {session_id}")
                else:
                    logger.info(f"Successfully deleted session with session_id: {session_id}")
            except Exception as e:
                logger.error(f"Error deleting session: {e}")
                raise

    def drop(self) -> None:
        if self.table_exists():
            logger.debug(f"Deleting table: {self.table_name}")
            self.table.drop(self.db_engine)

    def upgrade_schema(self) -> None:
        pass
