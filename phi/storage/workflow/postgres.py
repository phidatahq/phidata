import time
from typing import Optional, Any, List
from datetime import datetime

try:
    from sqlalchemy import create_engine, Engine, MetaData, Table, Column, String, JSON, inspect
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.orm import Session, sessionmaker
    from sqlalchemy.sql.expression import select
except ImportError:
    raise ImportError("`sqlalchemy` not installed. Please install it with `pip install sqlalchemy`")

from phi.workflow import WorkflowSession
from phi.storage.workflow.base import WorkflowStorage
from phi.utils.log import logger


class PostgresWorkflowStorage(WorkflowStorage):
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
        This class provides workflow storage using a PostgreSQL database.

        The following order is used to determine the database connection:
            1. Use the db_engine if provided
            2. Use the db_url
            3. Raise an error if neither is provided

        Args:
            table_name: The name of the table to store Workflow sessions.
            schema: The schema to use for the table. Defaults to "ai".
            db_url: The database URL to connect to.
            db_engine: The database engine to use.
            schema_version: The version of the schema to use.
            auto_upgrade_schema: Whether to automatically upgrade the schema.
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
        self.engine: Engine = _engine
        self.metadata: MetaData = MetaData(schema=self.schema)

        # Table schema version
        self.schema_version: int = schema_version
        # Automatically upgrade schema if True
        self.auto_upgrade_schema: bool = auto_upgrade_schema

        # Database session
        self.SessionLocal: sessionmaker[Session] = sessionmaker(bind=self.engine)
        # Database table for storage
        self.table: Table = self.get_table()
        
        # Ensure the table exists
        self.create()
        
        logger.debug(f"Created PostgresWorkflowStorage: '{self.schema}.{self.table_name}'")

    def get_table(self) -> Table:
        return self._create_table()

    def _create_table(self) -> Table:
        return Table(
            self.table_name,
            self.metadata,
            # Session UUID: Primary Key
            Column("session_id", String, primary_key=True),
            # ID of the workflow that this session is associated with
            Column("workflow_id", String),
            # ID of the user interacting with this workflow
            Column("user_id", String),
            # Workflow Memory
            Column("memory", JSON),
            # Workflow Metadata
            Column("workflow_data", JSON),
            # User Metadata
            Column("user_data", JSON),
            # Session Metadata
            Column("session_data", JSON),
            # Session state stored in the database
            Column("session_state", JSON),
            # The Unix timestamp of when this session was created.
            Column("created_at", postgresql.INTEGER, default=lambda: int(time.time())),
            # The Unix timestamp of when this session was last updated.
            Column("updated_at", postgresql.INTEGER, onupdate=lambda: int(time.time())),
        )

    def create(self) -> None:
        if not self.table_exists():
            logger.info(f"Creating table '{self.schema}.{self.table_name}'")
            self.metadata.create_all(self.engine)
        else:
            logger.debug(f"Table '{self.schema}.{self.table_name}' already exists")

    def read(self, session_id: str, user_id: Optional[str] = None) -> Optional[WorkflowSession]:
        with self.SessionLocal() as db_session:
            stmt = select(self.table).where(self.table.c.session_id == session_id)
            if user_id:
                stmt = stmt.where(self.table.c.user_id == user_id)
            result = db_session.execute(stmt).fetchone()
            if result:
                return WorkflowSession(**result['session_state'])
        return None

    def get_all_session_ids(self, user_id: Optional[str] = None, workflow_id: Optional[str] = None) -> List[str]:
        with self.SessionLocal() as db_session:
            stmt = select(self.table.c.session_id)
            if user_id:
                stmt = stmt.where(self.table.c.user_id == user_id)
            if workflow_id:
                stmt = stmt.where(self.table.c.workflow_id == workflow_id)
            results = db_session.execute(stmt).fetchall()
            return [row[0] for row in results]

    def get_all_sessions(
        self, user_id: Optional[str] = None, workflow_id: Optional[str] = None
    ) -> List[WorkflowSession]:
        with self.SessionLocal() as db_session:
            stmt = select(self.table)
            if user_id:
                stmt = stmt.where(self.table.c.user_id == user_id)
            if workflow_id:
                stmt = stmt.where(self.table.c.workflow_id == workflow_id)
            results = db_session.execute(stmt).fetchall()
            return [WorkflowSession(**row['session_state']) for row in results]

    def upsert(self, session: WorkflowSession) -> Optional[WorkflowSession]:
        with self.SessionLocal() as db_session:
            now = int(time.time())
            stmt = postgresql.insert(self.table).values(
                session_id=session.session_id,
                workflow_id=session.workflow_id,
                user_id=session.user_id,
                memory=session.memory,
                workflow_data=session.workflow_data,
                user_data=session.user_data,
                session_data=session.session_data,
                session_state=session.model_dump(),
                created_at=now,
                updated_at=now,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=['session_id'],
                set_={
                    'workflow_id': stmt.excluded.workflow_id,
                    'user_id': stmt.excluded.user_id,
                    'memory': stmt.excluded.memory,
                    'workflow_data': stmt.excluded.workflow_data,
                    'user_data': stmt.excluded.user_data,
                    'session_data': stmt.excluded.session_data,
                    'session_state': stmt.excluded.session_state,
                    'updated_at': stmt.excluded.updated_at,
                }
            )
            db_session.execute(stmt)
            db_session.commit()
            return session

    def delete_session(self, session_id: Optional[str] = None):
        if session_id is None:
            raise ValueError("session_id must be provided")
        with self.SessionLocal() as db_session:
            stmt = self.table.delete().where(self.table.c.session_id == session_id)
            db_session.execute(stmt)
            db_session.commit()

    def table_exists(self) -> bool:
        try:
            inspector = inspect(self.engine)
            return inspector.has_table(self.table_name, schema=self.schema)
        except Exception as e:
            logger.error(f"Error checking if table exists: {e}")
            return False

    def drop(self) -> None:
        if self.table_exists():
            self.metadata.drop_all(self.engine)
        else:
            logger.debug(f"Table {self.table_name} does not exist, nothing to drop.")

    def upgrade_schema(self) -> None:
        pass

    def __deepcopy__(self, memo):
        """
        Create a deep copy of the PostgresWorkflowStorage instance, handling unpickleable attributes.

        Args:
            memo (dict): A dictionary of objects already copied during the current copying pass.

        Returns:
            PostgresWorkflowStorage: A deep-copied instance of PostgresWorkflowStorage.
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
            # Reuse engine and SessionLocal without copying
            elif k in {"engine", "SessionLocal"}:
                setattr(copied_obj, k, v)
            else:
                setattr(copied_obj, k, deepcopy(v, memo))

        # Recreate metadata and table for the copied instance
        copied_obj.metadata = MetaData(schema=copied_obj.schema)
        copied_obj.table = copied_obj._create_table()

        return copied_obj
