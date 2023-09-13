from typing import Optional, Dict, Any, List

try:
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.engine import create_engine, Engine
    from sqlalchemy.engine.row import Row
    from sqlalchemy.inspection import inspect
    from sqlalchemy.orm import Session, sessionmaker
    from sqlalchemy.schema import MetaData, Table, Column
    from sqlalchemy.sql.expression import text, select
    from sqlalchemy.types import DateTime, String, BigInteger
except ImportError:
    raise ImportError("`sqlalchemy` not installed")

try:
    from psycopg.errors import UndefinedTable
except ImportError:
    raise ImportError("`psycopg` not installed")

from phi.conversation.schemas import ConversationRow
from phi.conversation.storage.base import ConversationStorage
from phi.utils.log import logger


class PgConversationStorage(ConversationStorage):
    def __init__(
        self,
        table_name: str,
        schema: Optional[str] = "llm",
        db_url: Optional[str] = None,
        db_engine: Optional[Engine] = None,
    ):
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
            # Database ID/Primary key for this conversation.
            Column("id", BigInteger, primary_key=True, autoincrement=True),
            # Conversation name
            Column("name", String),
            # The name of the user participating in this conversation.
            Column("user_name", String),
            # The persona of the user participating in this conversation.
            Column("user_persona", String),
            # True if this conversation is active.
            Column("is_active", postgresql.BOOLEAN, server_default=text("true")),
            # -*- LLM data (name, model, etc.)
            Column("llm", postgresql.JSONB),
            # -*- Conversation history
            Column("history", postgresql.JSONB),
            # Extra data associated with this conversation.
            Column("extra_data", postgresql.JSONB),
            # The timestamp of when this conversation was created.
            Column("created_at", DateTime(timezone=True), server_default=text("now()")),
            # The timestamp of when this conversation was last updated.
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
                with self.Session() as sess:
                    with sess.begin():
                        logger.debug(f"Creating schema: {self.schema}")
                        sess.execute(text(f"create schema if not exists {self.schema};"))
            logger.debug(f"Creating table: {self.table_name}")
            self.table.create(self.db_engine)

    def _read(self, session: Session, conversation_id: int) -> Optional[Row[Any]]:
        stmt = select(self.table).where(self.table.c.id == conversation_id)
        try:
            return session.execute(stmt).first()
        except UndefinedTable:
            # Create table if it does not exist
            self.create()
        except Exception as e:
            logger.warning(e)
        return None

    def read(self, conversation_id: int) -> Optional[ConversationRow]:
        with self.Session() as sess:
            with sess.begin():
                existing_row: Optional[Row[Any]] = self._read(session=sess, conversation_id=conversation_id)
                return ConversationRow.model_validate(existing_row) if existing_row is not None else None

    def get_all_conversation_ids(self, user_name: str) -> List[int]:
        conversation_ids: List[int] = []
        try:
            with self.Session() as sess:
                with sess.begin():
                    # get all conversation ids for this user
                    stmt = select(self.table).where(self.table.c.user_name == user_name)
                    # order by id desc
                    stmt = stmt.order_by(self.table.c.id.desc())
                    # execute query
                    rows = sess.execute(stmt).fetchall()
                    for row in rows:
                        if row is not None and row.id is not None:
                            conversation_ids.append(row.id)
        except UndefinedTable:
            logger.debug(f"Table does not exist: {self.table.name}")
            pass
        return conversation_ids

    def get_all_conversations(self, user_name: str) -> List[ConversationRow]:
        conversation_ids: List[ConversationRow] = []
        try:
            with self.Session() as sess:
                with sess.begin():
                    # get all conversation ids for this user
                    stmt = select(self.table).where(self.table.c.user_name == user_name)
                    # order by id desc
                    stmt = stmt.order_by(self.table.c.id.desc())
                    # execute query
                    rows = sess.execute(stmt).fetchall()
                    for row in rows:
                        if row.id is not None:
                            conversation_ids.append(ConversationRow.model_validate(row))
        except UndefinedTable:
            logger.debug(f"Table does not exist: {self.table.name}")
            pass
        return conversation_ids

    def upsert(self, conversation: ConversationRow) -> Optional[ConversationRow]:
        """
        Create a new conversation if it does not exist, otherwise update the existing conversation.
        """
        with self.Session() as sess:
            with sess.begin():
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

                    insert_stmt = postgresql.insert(self.table).values(**values_to_insert)
                    try:
                        result = sess.execute(insert_stmt)
                    except UndefinedTable:
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

                    update_stmt = (
                        self.table.update().where(self.table.c.id == conversation.id).values(**values_to_update)
                    )
                    sess.execute(update_stmt)
        return self.read(conversation_id=conversation.id)

    def end(self, conversation_id: int) -> None:
        with self.Session() as sess:
            with sess.begin():
                # Check if conversation exists in the database
                existing_row: Optional[Row[Any]] = self._read(session=sess, conversation_id=conversation_id)
                # If conversation exists, set is_active to False
                if existing_row is not None:
                    stmt = self.table.update().where(self.table.c.id == conversation_id).values(is_active=False)
                    sess.execute(stmt)

    def delete(self) -> None:
        if self.table_exists():
            logger.debug(f"Deleting table: {self.table_name}")
            self.table.drop(self.db_engine)
