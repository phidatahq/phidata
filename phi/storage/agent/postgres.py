from typing import Optional, Any, List

try:
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.engine import create_engine, Engine
    from sqlalchemy.engine.result import Row
    from sqlalchemy.inspection import inspect
    from sqlalchemy.orm import sessionmaker, scoped_session
    from sqlalchemy.schema import MetaData, Table, Column, Index
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
        Initialize Agent storage using a PostgreSQL table.

        The database connection is determined in the following order:
        1. Use the provided db_engine
        2. Use the provided db_url to create a new engine

        Args:
            table_name (str): Name of the table to store Agent sessions.
            schema (Optional[str], optional): Schema to store the table in. Defaults to "ai".
            db_url (Optional[str], optional): Database URL for connection. Defaults to None.
            db_engine (Optional[Engine], optional): SQLAlchemy database engine. Defaults to None.
            schema_version (int, optional): Version of the schema. Defaults to 1.
            auto_upgrade_schema (bool, optional): Automatically upgrade schema if True. Defaults to False.

        Raises:
            ValueError: If neither db_url nor db_engine is provided.
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
        self.Session: scoped_session = scoped_session(sessionmaker(bind=self.db_engine))
        # Database table for storage
        self.table: Table = self.get_table()
        logger.debug(f"Created PgAgentStorage: '{self.schema}.{self.table_name}'")

    def get_table_v1(self) -> Table:
        """
        Define the table schema for version 1.

        Returns:
            Table: SQLAlchemy Table object representing the schema.
        """
        table = Table(
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

        # Add indexes
        Index(f"idx_{self.table_name}_user_id", table.c.user_id)
        Index(f"idx_{self.table_name}_agent_id", table.c.agent_id)
        Index(f"idx_{self.table_name}_session_id", table.c.session_id)

        return table

    def get_table(self) -> Table:
        """
        Get the appropriate table schema based on the schema version.

        Returns:
            Table: SQLAlchemy Table object for the current schema version.

        Raises:
            ValueError: If an unsupported schema version is specified.
        """
        if self.schema_version == 1:
            return self.get_table_v1()
        else:
            raise ValueError(f"Unsupported schema version: {self.schema_version}")

    def table_exists(self) -> bool:
        """
        Check if the table exists in the database.

        Returns:
            bool: True if the table exists, False otherwise.
        """
        logger.debug(f"Checking if table exists: {self.table.name}")
        try:
            return inspect(self.db_engine).has_table(self.table.name, schema=self.schema)
        except Exception as e:
            logger.error(e)
            return False

    def create(self) -> None:
        """
        Create the table if it does not exist.
        """
        if not self.table_exists():
            try:
                with self.Session() as sess, sess.begin():
                    if self.schema is not None:
                        logger.debug(f"Creating schema: {self.schema}")
                        sess.execute(text(f"CREATE SCHEMA IF NOT EXISTS {self.schema};"))
                logger.debug(f"Creating table: {self.table_name}")
                self.table.create(self.db_engine, checkfirst=True)
            except Exception as e:
                logger.error(f"Could not create table: '{self.table.fullname}': {e}")

    def read(self, session_id: str) -> Optional[AgentSession]:
        """
        Read and return an AgentSession from the database.

        Args:
            session_id (str): ID of the session to read.

        Returns:
            Optional[AgentSession]: AgentSession object if found, None otherwise.
        """
        try:
            with self.Session() as sess:
                stmt = select(self.table).where(self.table.c.session_id == session_id)
                existing_row: Optional[Row[Any]] = sess.execute(stmt).first()
                return AgentSession.model_validate(existing_row) if existing_row is not None else None
        except Exception as e:
            logger.debug(f"Exception reading from table: {e}")
            logger.debug(f"Table does not exist: {self.table.name}")
            logger.debug("Creating table for future transactions")
            self.create()
        return None

    def get_all_session_ids(self, user_id: Optional[str] = None, agent_id: Optional[str] = None) -> List[str]:
        """
        Retrieve all session IDs, optionally filtered by user_id and/or agent_id.

        Args:
            user_id (Optional[str], optional): User ID to filter by. Defaults to None.
            agent_id (Optional[str], optional): Agent ID to filter by. Defaults to None.

        Returns:
            List[str]: List of session IDs matching the criteria.
        """
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
            logger.debug("Creating table for future transactions")
            self.create()
        return session_ids

    def get_all_sessions(self, user_id: Optional[str] = None, agent_id: Optional[str] = None) -> List[AgentSession]:
        """
        Retrieve all sessions, optionally filtered by user_id and/or agent_id.

        Args:
            user_id (Optional[str], optional): User ID to filter by. Defaults to None.
            agent_id (Optional[str], optional): Agent ID to filter by. Defaults to None.

        Returns:
            List[AgentSession]: List of AgentSession objects matching the criteria.
        """
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
            logger.debug("Creating table for future transactions")
            self.create()
        return sessions

    def upsert(self, session: AgentSession, create_and_retry: bool = True) -> Optional[AgentSession]:
        """
        Create or update an AgentSession in the database.

        Args:
            session (AgentSession): The session data to upsert.
            create_and_retry (bool, optional): Retry upsert after creating the table if True. Defaults to True.
        Returns:
            Optional[AgentSession]: The upserted AgentSession, or None if operation failed.
        """

        try:
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

                sess.execute(stmt)
        except Exception as e:
            logger.debug(f"Exception upserting into table: {e}")
            logger.debug(f"Table does not exist: {self.table.name}")
            logger.debug("Creating table for future transactions")
            self.create()
            if create_and_retry:
                return self.upsert(session, create_and_retry=False)
            return None
        return self.read(session_id=session.session_id)

    def delete_session(self, session_id: Optional[str] = None):
        """
        Delete a session from the database.

        Args:
            session_id (Optional[str], optional): ID of the session to delete. Defaults to None.

        Raises:
            Exception: If an error occurs during deletion.
        """
        if session_id is None:
            logger.warning("No session_id provided for deletion.")
            return

        try:
            with self.Session() as sess, sess.begin():
                # Delete the session with the given session_id
                delete_stmt = self.table.delete().where(self.table.c.session_id == session_id)
                result = sess.execute(delete_stmt)

                if result.rowcount == 0:
                    logger.warning(f"No session found with session_id: {session_id}")
                else:
                    logger.info(f"Successfully deleted session with session_id: {session_id}")
        except Exception as e:
            logger.error(f"Error deleting session: {e}")

    def drop(self) -> None:
        """
        Drop the table from the database if it exists.
        """
        if self.table_exists():
            logger.debug(f"Deleting table: {self.table_name}")
            self.table.drop(self.db_engine)

    def upgrade_schema(self) -> None:
        """
        Upgrade the schema to the latest version.
        This method is currently a placeholder and does not perform any actions.
        """
        pass

    def __deepcopy__(self, memo):
        """
        Create a deep copy of the PgAgentStorage instance, handling unpickleable attributes.

        Args:
            memo (dict): A dictionary of objects already copied during the current copying pass.

        Returns:
            PgAgentStorage: A deep-copied instance of PgAgentStorage.
        """
        from copy import deepcopy

        # Create a new instance without calling __init__
        cls = self.__class__
        copied_obj = cls.__new__(cls)
        memo[id(self)] = copied_obj

        # Deep copy attributes
        for k, v in self.__dict__.items():
            if k in {"metadata", "table"}:
                continue
            # Reuse db_engine and Session without copying
            elif k in {"db_engine", "Session"}:
                setattr(copied_obj, k, v)
            else:
                setattr(copied_obj, k, deepcopy(v, memo))

        # Recreate metadata and table for the copied instance
        copied_obj.metadata = MetaData(schema=copied_obj.schema)
        copied_obj.table = copied_obj.get_table()

        return copied_obj
