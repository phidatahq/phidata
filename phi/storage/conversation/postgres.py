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

from phi.conversation.row import ConversationRow
from phi.storage.conversation.base import ConversationStorage
from phi.utils.log import logger


class PgConversationStorage(ConversationStorage):
    def __init__(
        self,
        table_name: str,
        schema: Optional[str] = "llm",
        db_url: Optional[str] = None,
        db_engine: Optional[Engine] = None,
    ):
        """
        This class provides conversation storage using a postgres database.

        The following order is used to determine the database connection:
            1. Use the db_engine if provided
            2. Use the db_url

        :param table_name: The name of the table to store conversations in.
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
            # Primary key for this conversation.
            Column("id", String, primary_key=True),
            # Conversation name
            Column("name", String),
            # Name and type of user participating in this conversation.
            Column("user_name", String),
            Column("user_type", String),
            # True if this conversation is active.
            Column("is_active", postgresql.BOOLEAN, server_default=text("true")),
            # -*- LLM data (name, model, etc.)
            Column("llm", postgresql.JSONB),
            # -*- Conversation memory
            Column("memory", postgresql.JSONB),
            # Metadata associated with this conversation.
            Column("meta_data", postgresql.JSONB),
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
                with self.Session() as sess, sess.begin():
                    logger.debug(f"Creating schema: {self.schema}")
                    sess.execute(text(f"create schema if not exists {self.schema};"))
            logger.debug(f"Creating table: {self.table_name}")
            self.table.create(self.db_engine)

    def _read(self, session: Session, conversation_id: str) -> Optional[Row[Any]]:
        stmt = select(self.table).where(self.table.c.id == conversation_id)
        try:
            return session.execute(stmt).first()
        except Exception:
            # Create table if it does not exist
            self.create()
        return None

    def read(self, conversation_id: str) -> Optional[ConversationRow]:
        with self.Session() as sess, sess.begin():
            existing_row: Optional[Row[Any]] = self._read(session=sess, conversation_id=conversation_id)
            return ConversationRow.model_validate(existing_row) if existing_row is not None else None

    def get_all_conversation_ids(self, user_name: Optional[str] = None) -> List[str]:
        conversation_ids: List[str] = []
        try:
            with self.Session() as sess, sess.begin():
                # get all conversation ids for this user
                stmt = select(self.table)
                if user_name is not None:
                    stmt = stmt.where(self.table.c.user_name == user_name)
                # order by created_at desc
                stmt = stmt.order_by(self.table.c.created_at.desc())
                # execute query
                rows = sess.execute(stmt).fetchall()
                for row in rows:
                    if row is not None and row.id is not None:
                        conversation_ids.append(row.id)
        except Exception:
            logger.debug(f"Table does not exist: {self.table.name}")
        return conversation_ids

    def get_all_conversations(self, user_name: Optional[str] = None) -> List[ConversationRow]:
        conversations: List[ConversationRow] = []
        try:
            with self.Session() as sess, sess.begin():
                # get all conversation ids for this user
                stmt = select(self.table)
                if user_name is not None:
                    stmt = stmt.where(self.table.c.user_name == user_name)
                # order by created_at desc
                stmt = stmt.order_by(self.table.c.created_at.desc())
                # execute query
                rows = sess.execute(stmt).fetchall()
                for row in rows:
                    if row.id is not None:
                        conversations.append(ConversationRow.model_validate(row))
        except Exception:
            logger.debug(f"Table does not exist: {self.table.name}")
        return conversations

    def upsert(self, conversation: ConversationRow) -> Optional[ConversationRow]:
        """
        Create a new conversation if it does not exist, otherwise update the existing conversation.
        """

        with self.Session() as sess, sess.begin():
            # Create an insert statement
            stmt = postgresql.insert(self.table).values(
                id=conversation.id,
                name=conversation.name,
                user_name=conversation.user_name,
                user_type=conversation.user_type,
                is_active=conversation.is_active,
                llm=conversation.llm,
                memory=conversation.memory,
                meta_data=conversation.meta_data,
                extra_data=conversation.extra_data,
            )

            # Define the upsert if the id already exists
            # See: https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#postgresql-insert-on-conflict
            stmt = stmt.on_conflict_do_update(
                index_elements=["id"],
                set_=dict(
                    name=conversation.name,
                    user_name=conversation.user_name,
                    user_type=conversation.user_type,
                    is_active=conversation.is_active,
                    llm=conversation.llm,
                    memory=conversation.memory,
                    meta_data=conversation.meta_data,
                    extra_data=conversation.extra_data,
                ),  # The updated value for each column
            )

            try:
                sess.execute(stmt)
            except Exception:
                # Create table and try again
                self.create()
                sess.execute(stmt)
        return self.read(conversation_id=conversation.id)

    def end(self, conversation_id: str) -> None:
        with self.Session() as sess, sess.begin():
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
