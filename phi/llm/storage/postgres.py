from typing import Optional, Dict, Any

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

from phi.llm.conversation.schemas import ConversationRow
from phi.llm.storage.base import LLMStorage
from phi.utils.log import logger


class PgConversationStorage(LLMStorage):
    def __init__(
        self,
        table_name: str,
        schema: Optional[str] = None,
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
            # The ID of this conversation.
            Column("id", BigInteger, primary_key=True, autoincrement=True),
            # The name of this conversation.
            Column("name", String),
            # The ID of the user who is participating in this conversation.
            Column("user_id", String),
            # The persona of the user who is participating in this conversation.
            Column("user_persona", String),
            # The data of the user who is participating in this conversation.
            Column("user_data", postgresql.JSONB),
            # True if this conversation is active.
            Column("is_active", postgresql.BOOLEAN, server_default=text("true")),
            # The history of this conversation.
            Column("history", postgresql.JSONB),
            # The usage data of this conversation.
            Column("usage_data", postgresql.JSONB),
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

    def _read_conversation(self, session: Session, conversation_id: int, user_id: str) -> Optional[Row[Any]]:
        stmt = (
            select(self.table)
            .where(self.table.c.id == conversation_id)
            .where(self.table.c.user_id == user_id)
            .where(self.table.c.is_active == True)  # noqa: E712
        )

        return session.execute(stmt).one()

    def read_conversation(self, conversation_id: int, user_id: str) -> Optional[ConversationRow]:
        with self.Session() as sess:
            with sess.begin():
                existing_row: Optional[Row[Any]] = self._read_conversation(
                    session=sess, conversation_id=conversation_id, user_id=user_id
                )
                return ConversationRow.model_validate(existing_row) if existing_row is not None else None

    def upsert_conversation(self, conversation: ConversationRow) -> Optional[ConversationRow]:
        """
        Create a new conversation if it does not exist, otherwise update the existing conversation.
        """
        with self.Session() as sess:
            with sess.begin():
                # Conversation exists if conversation.id is not None
                if conversation.id is None:
                    values_to_insert: Dict[str, Any] = {
                        "user_id": conversation.user_id,
                        "user_persona": conversation.user_persona,
                        "user_data": conversation.user_data,
                        "history": conversation.history.model_dump(
                            include={"chat_history", "llm_history", "references"}
                        ),
                        "usage_data": conversation.usage_data,
                    }
                    if conversation.name is not None:
                        values_to_insert["name"] = conversation.name

                    insert_stmt = postgresql.insert(self.table).values(**values_to_insert)
                    result = sess.execute(insert_stmt)
                    conversation.id = result.inserted_primary_key[0]  # type: ignore
                else:
                    values_to_update: Dict[str, Any] = {}
                    if conversation.name is not None:
                        values_to_update["name"] = conversation.name
                    if conversation.user_persona is not None:
                        values_to_update["user_persona"] = conversation.user_persona
                    if conversation.user_data is not None:
                        values_to_update["user_data"] = conversation.user_data
                    if conversation.history is not None:
                        values_to_update["history"] = conversation.history.model_dump(
                            include={"chat_history", "llm_history", "references"}
                        )
                    if conversation.usage_data is not None:
                        values_to_update["usage_data"] = conversation.usage_data

                    update_stmt = (
                        self.table.update().where(self.table.c.id == conversation.id).values(**values_to_update)
                    )
                    sess.execute(update_stmt)
        return self.read_conversation(conversation_id=conversation.id, user_id=conversation.user_id)

    def end_conversation(self, conversation_id: int, user_id: str) -> None:
        with self.Session() as sess:
            with sess.begin():
                existing_row: Optional[Row[Any]] = self._read_conversation(
                    session=sess, conversation_id=conversation_id, user_id=user_id
                )
                # Check if conversation exists in the database
                if existing_row is not None:
                    stmt = (
                        self.table.update()
                        .where(self.table.c.id == conversation_id)
                        .where(self.table.c.user_id == user_id)
                        .values(is_active=False)
                    )
                    sess.execute(stmt)

    def delete(self) -> None:
        if self.table_exists():
            logger.debug(f"Deleting table: {self.table_name}")
            self.table.drop(self.db_engine)
