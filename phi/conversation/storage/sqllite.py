from typing import Optional, Dict, Any, List

try:
    from sqlalchemy.dialects import sqlite
    from sqlalchemy.engine import create_engine, Engine
    from sqlalchemy.engine.row import Row
    from sqlalchemy.inspection import inspect
    from sqlalchemy.orm import Session, sessionmaker
    from sqlalchemy.schema import MetaData, Table, Column
    from sqlalchemy.sql.expression import select
    from sqlalchemy.types import String, Integer
except ImportError:
    raise ImportError("`sqlalchemy` not installed")

from sqlite3 import OperationalError

from phi.conversation.schemas import ConversationRow
from phi.conversation.storage.base import ConversationStorage
from phi.utils.dttm import current_datetime
from phi.utils.log import logger


class SqlConversationStorage(ConversationStorage):
    def __init__(
        self,
        table_name: str,
        db_url: Optional[str] = None,
        db_file: Optional[str] = None,
        db_engine: Optional[Engine] = None,
    ):
        """
        :param table_name: The name of the table to store conversations in.
        :param db_url: The database URL to connect to.
        :param db_file: The database file to connect to.
        :param db_engine: The database engine to use.

        To connect to the database:
            Use the db_engine if provided
            Otherwise, use the db_url if provided
            Otherwise, use the db_file if provided
            Otherwise, create a new in-memory database
        """
        _engine: Optional[Engine] = db_engine
        if _engine is None and db_url is not None:
            _engine = create_engine(db_url)
        elif _engine is None and db_file is not None:
            _engine = create_engine(f"sqlite:///{db_file}")
        else:
            _engine = create_engine("sqlite://")

        if _engine is None:
            raise ValueError("Must provide either db_url, db_file or db_engine")

        # Database attributes
        self.table_name: str = table_name
        self.db_url: Optional[str] = db_url
        self.db_engine: Engine = _engine
        self.metadata: MetaData = MetaData()

        # Database session
        self.Session: sessionmaker[Session] = sessionmaker(bind=self.db_engine)

        # Database table for storage
        self.table: Table = self.get_table()

    def get_table(self) -> Table:
        return Table(
            self.table_name,
            self.metadata,
            # Database ID/Primary key for this conversation.
            Column("id", Integer, primary_key=True),
            # Conversation name
            Column("name", String),
            # The name of the user participating in this conversation.
            Column("user_name", String),
            # The persona of the user participating in this conversation.
            Column("user_persona", String),
            # True if this conversation is active.
            Column("is_active", sqlite.BOOLEAN, default=True),
            # -*- LLM data (name, model, etc.)
            Column("llm", sqlite.JSON),
            # -*- Conversation history
            Column("history", sqlite.JSON),
            # Extra data associated with this conversation.
            Column("extra_data", sqlite.JSON),
            # The timestamp of when this conversation was created.
            Column("created_at", sqlite.DATETIME, default=current_datetime()),
            # The timestamp of when this conversation was last updated.
            Column("updated_at", sqlite.DATETIME, onupdate=current_datetime()),
            extend_existing=True,
            sqlite_autoincrement=True,
        )

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
            self.table.create(self.db_engine)

    def _read(self, session: Session, conversation_id: int) -> Optional[Row[Any]]:
        stmt = select(self.table).where(self.table.c.id == conversation_id)
        try:
            return session.execute(stmt).first()
        except OperationalError:
            # Create table if it does not exist
            self.create()
        except Exception as e:
            logger.warning(e)
        return None

    def read(self, conversation_id: int) -> Optional[ConversationRow]:
        with self.Session() as sess:
            existing_row: Optional[Row[Any]] = self._read(session=sess, conversation_id=conversation_id)
            return ConversationRow.model_validate(existing_row) if existing_row is not None else None

    def get_all_conversation_ids(self, user_name: str) -> List[int]:
        conversation_ids: List[int] = []
        try:
            with self.Session() as sess:
                # get all conversation ids for this user
                stmt = select(self.table).where(self.table.c.user_name == user_name)
                # order by id desc
                stmt = stmt.order_by(self.table.c.id.desc())
                # execute query
                rows = sess.execute(stmt).fetchall()
                for row in rows:
                    if row is not None and row.id is not None:
                        conversation_ids.append(row.id)
        except OperationalError:
            logger.debug(f"Table does not exist: {self.table.name}")
            pass
        return conversation_ids

    def get_all_conversations(self, user_name: str) -> List[ConversationRow]:
        conversation_ids: List[ConversationRow] = []
        try:
            with self.Session() as sess:
                # get all conversation ids for this user
                stmt = select(self.table).where(self.table.c.user_name == user_name)
                # order by id desc
                stmt = stmt.order_by(self.table.c.id.desc())
                # execute query
                rows = sess.execute(stmt).fetchall()
                for row in rows:
                    if row.id is not None:
                        conversation_ids.append(ConversationRow.model_validate(row))
        except OperationalError:
            logger.debug(f"Table does not exist: {self.table.name}")
            pass
        return conversation_ids

    def upsert(self, conversation: ConversationRow) -> Optional[ConversationRow]:
        """
        Create a new conversation if it does not exist, otherwise update the existing conversation.
        """
        with self.Session() as sess:
            # Conversation exists if conversation.id is not None
            if conversation.id is None:
                values_to_insert: Dict[str, Any] = {
                    "name": conversation.name,
                    "user_name": conversation.user_name,
                    "user_persona": conversation.user_persona,
                    "is_active": conversation.is_active,
                    "llm": conversation.llm,
                    "history": conversation.history,
                    "extra_data": conversation.extra_data,
                }

                insert_stmt = sqlite.insert(self.table).values(**values_to_insert)
                try:
                    result = sess.execute(insert_stmt)
                except OperationalError:
                    # Create table if it does not exist
                    self.create()
                    result = sess.execute(insert_stmt)
                conversation.id = result.inserted_primary_key[0]  # type: ignore
            else:
                values_to_update: Dict[str, Any] = {}
                if conversation.name is not None:
                    values_to_update["name"] = conversation.name
                if conversation.user_name is not None:
                    values_to_update["user_name"] = conversation.user_name
                if conversation.user_persona is not None:
                    values_to_update["user_persona"] = conversation.user_persona
                if conversation.is_active is not None:
                    values_to_update["is_active"] = conversation.is_active
                if conversation.llm is not None:
                    values_to_update["llm"] = conversation.llm
                if conversation.history is not None:
                    values_to_update["history"] = conversation.history
                if conversation.extra_data is not None:
                    values_to_update["extra_data"] = conversation.extra_data

                update_stmt = self.table.update().where(self.table.c.id == conversation.id).values(**values_to_update)
                sess.execute(update_stmt)
            sess.commit()
        return self.read(conversation_id=conversation.id)

    def end(self, conversation_id: int) -> None:
        with self.Session() as sess:
            # Check if conversation exists in the database
            existing_row: Optional[Row[Any]] = self._read(session=sess, conversation_id=conversation_id)
            # If conversation exists, set is_active to False
            if existing_row is not None:
                stmt = self.table.update().where(self.table.c.id == conversation_id).values(is_active=False)
                sess.execute(stmt)
            sess.commit()

    def delete(self) -> None:
        if self.table_exists():
            logger.debug(f"Deleting table: {self.table_name}")
            self.table.drop(self.db_engine)
