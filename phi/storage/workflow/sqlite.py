import time
from pathlib import Path
from typing import Optional, Any, List

try:
    from sqlalchemy.dialects import sqlite
    from sqlalchemy.engine import create_engine, Engine
    from sqlalchemy.engine.row import Row
    from sqlalchemy.inspection import inspect
    from sqlalchemy.orm import Session, sessionmaker
    from sqlalchemy.schema import MetaData, Table, Column
    from sqlalchemy.sql.expression import select
    from sqlalchemy.types import String
except ImportError:
    raise ImportError("`sqlalchemy` not installed. Please install it with `pip install sqlalchemy`")

from phi.workflow import WorkflowSession
from phi.storage.workflow.base import WorkflowStorage
from phi.utils.log import logger


class SqlWorkflowStorage(WorkflowStorage):
    def __init__(
        self,
        table_name: str,
        db_url: Optional[str] = None,
        db_file: Optional[str] = None,
        db_engine: Optional[Engine] = None,
        schema_version: int = 1,
        auto_upgrade_schema: bool = False,
    ):
        """
        This class provides workflow storage using a sqlite database.

        The following order is used to determine the database connection:
            1. Use the db_engine if provided
            2. Use the db_url
            3. Use the db_file
            4. Create a new in-memory database

        Args:
            table_name: The name of the table to store Workflow sessions.
            db_url: The database URL to connect to.
            db_file: The database file to connect to.
            db_engine: The database engine to use.
        """
        _engine: Optional[Engine] = db_engine
        if _engine is None and db_url is not None:
            _engine = create_engine(db_url)
        elif _engine is None and db_file is not None:
            # Use the db_file to create the engine
            db_path = Path(db_file).resolve()
            # Ensure the directory exists
            db_path.parent.mkdir(parents=True, exist_ok=True)
            _engine = create_engine(f"sqlite:///{db_path}")
        else:
            _engine = create_engine("sqlite://")

        if _engine is None:
            raise ValueError("Must provide either db_url, db_file or db_engine")

        # Database attributes
        self.table_name: str = table_name
        self.db_url: Optional[str] = db_url
        self.db_engine: Engine = _engine
        self.metadata: MetaData = MetaData()

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
            # ID of the workflow that this session is associated with
            Column("workflow_id", String),
            # ID of the user interacting with this workflow
            Column("user_id", String),
            # Workflow Metadata
            Column("workflow_data", sqlite.JSON),
            # User Metadata
            Column("user_data", sqlite.JSON),
            # Session Metadata
            Column("session_data", sqlite.JSON),
            # Session state stored in the database
            Column("session_state", sqlite.JSON),
            # The Unix timestamp of when this session was created.
            Column("created_at", sqlite.INTEGER, default=lambda: int(time.time())),
            # The Unix timestamp of when this session was last updated.
            Column("updated_at", sqlite.INTEGER, onupdate=lambda: int(time.time())),
            extend_existing=True,
            sqlite_autoincrement=True,
        )

    def get_table(self) -> Table:
        if self.schema_version == 1:
            return self.get_table_v1()
        else:
            raise ValueError(f"Unsupported schema version: {self.schema_version}")

    def table_exists(self) -> bool:
        logger.debug(f"Checking if table exists: {self.table.name}")
        try:
            return inspect(self.db_engine).has_table(self.table.name)
        except Exception as e:
            logger.error(e)
            return False

    def create(self) -> None:
        if not self.table_exists():
            logger.debug(f"Creating table: {self.table.name}")
            self.table.create(self.db_engine, checkfirst=True)

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

    def read(self, session_id: str, user_id: Optional[str] = None) -> Optional[WorkflowSession]:
        try:
            with self.Session() as sess:
                stmt = select(self.table).where(self.table.c.session_id == session_id)
                if user_id:
                    stmt = stmt.where(self.table.c.user_id == user_id)
                existing_row: Optional[Row[Any]] = sess.execute(stmt).first()
                return WorkflowSession.model_validate(existing_row) if existing_row is not None else None
        except Exception as e:
            logger.debug(f"Exception reading from table: {e}")
            logger.debug(f"Table does not exist: {self.table.name}")
            logger.debug("Creating table for future transactions")
            self.create()
        return None

    def get_all_session_ids(self, user_id: Optional[str] = None, workflow_id: Optional[str] = None) -> List[str]:
        session_ids: List[str] = []
        try:
            with self.Session() as sess, sess.begin():
                # get all session_ids for this user
                stmt = select(self.table)
                if user_id is not None:
                    stmt = stmt.where(self.table.c.user_id == user_id)
                if workflow_id is not None:
                    stmt = stmt.where(self.table.c.workflow_id == workflow_id)
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

    def get_all_sessions(
        self, user_id: Optional[str] = None, workflow_id: Optional[str] = None
    ) -> List[WorkflowSession]:
        sessions: List[WorkflowSession] = []
        try:
            with self.Session() as sess, sess.begin():
                # get all sessions for this user
                stmt = select(self.table)
                if user_id is not None:
                    stmt = stmt.where(self.table.c.user_id == user_id)
                if workflow_id is not None:
                    stmt = stmt.where(self.table.c.workflow_id == workflow_id)
                # order by created_at desc
                stmt = stmt.order_by(self.table.c.created_at.desc())
                # execute query
                rows = sess.execute(stmt).fetchall()
                for row in rows:
                    if row.session_id is not None:
                        sessions.append(WorkflowSession.model_validate(row))
        except Exception as e:
            logger.debug(f"Exception reading from table: {e}")
            logger.debug(f"Table does not exist: {self.table.name}")
            logger.debug("Creating table for future transactions")
            self.create()
        return sessions

    def upsert(self, session: WorkflowSession, create_and_retry: bool = True) -> Optional[WorkflowSession]:
        """Create a new WorkflowSession if it does not exist, otherwise update the existing WorkflowSession."""

        try:
            with self.Session() as sess, sess.begin():
                # Create an insert statement
                stmt = sqlite.insert(self.table).values(
                    session_id=session.session_id,
                    workflow_id=session.workflow_id,
                    user_id=session.user_id,
                    workflow_data=session.workflow_data,
                    user_data=session.user_data,
                    session_data=session.session_data,
                    session_state=session.session_state,
                )

                # Define the upsert if the session_id already exists
                # See: https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#insert-on-conflict-upsert
                stmt = stmt.on_conflict_do_update(
                    index_elements=["session_id"],
                    set_=dict(
                        workflow_id=session.workflow_id,
                        user_id=session.user_id,
                        workflow_data=session.workflow_data,
                        user_data=session.user_data,
                        session_data=session.session_data,
                        session_state=session.session_state,
                        updated_at=int(time.time()),
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
        if self.table_exists():
            logger.debug(f"Deleting table: {self.table_name}")
            self.table.drop(self.db_engine)

    def upgrade_schema(self) -> None:
        pass

    def __deepcopy__(self, memo):
        """
        Create a deep copy of the SqlWorkflowStorage instance, handling unpickleable attributes.

        Args:
            memo (dict): A dictionary of objects already copied during the current copying pass.

        Returns:
            SqlWorkflowStorage: A deep-copied instance of SqlWorkflowStorage.
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
        copied_obj.metadata = MetaData()
        copied_obj.table = copied_obj.get_table()

        return copied_obj
