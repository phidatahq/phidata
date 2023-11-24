# from typing import Optional, Any, List
#
# try:
#     from sqlalchemy.dialects import sqlite
#     from sqlalchemy.engine import create_engine, Engine
#     from sqlalchemy.engine.row import Row
#     from sqlalchemy.inspection import inspect
#     from sqlalchemy.orm import Session, sessionmaker
#     from sqlalchemy.schema import MetaData, Table, Column
#     from sqlalchemy.sql.expression import select
#     from sqlalchemy.types import String
# except ImportError:
#     raise ImportError("`sqlalchemy` not installed")
#
# from sqlite3 import OperationalError
#
# from phi.conversation.schemas import ConversationRow
# from phi.conversation.storage.base import ConversationStorage
# from phi.utils.dttm import current_datetime
# from phi.utils.log import logger
#
#
# class SqlConversationStorage(ConversationStorage):
#     def __init__(
#         self,
#         table_name: str,
#         db_url: Optional[str] = None,
#         db_file: Optional[str] = None,
#         db_engine: Optional[Engine] = None,
#     ):
#         """
#         This class provides conversation storage using a sqllite database.
#
#         The following order is used to determine the database connection:
#             1. Use the db_engine if provided
#             2. Use the db_url
#             3. Use the db_file
#             4. Create a new in-memory database
#
#         :param table_name: The name of the table to store conversations in.
#         :param db_url: The database URL to connect to.
#         :param db_file: The database file to connect to.
#         :param db_engine: The database engine to use.
#         """
#         _engine: Optional[Engine] = db_engine
#         if _engine is None and db_url is not None:
#             _engine = create_engine(db_url)
#         elif _engine is None and db_file is not None:
#             _engine = create_engine(f"sqlite:///{db_file}")
#         else:
#             _engine = create_engine("sqlite://")
#
#         if _engine is None:
#             raise ValueError("Must provide either db_url, db_file or db_engine")
#
#         # Database attributes
#         self.table_name: str = table_name
#         self.db_url: Optional[str] = db_url
#         self.db_engine: Engine = _engine
#         self.metadata: MetaData = MetaData()
#
#         # Database session
#         self.Session: sessionmaker[Session] = sessionmaker(bind=self.db_engine)
#
#         # Database table for storage
#         self.table: Table = self.get_table()
#
#     def get_table(self) -> Table:
#         return Table(
#             self.table_name,
#             self.metadata,
#             # Database ID/Primary key for this conversation.
#             Column("id", String, primary_key=True),
#             # Conversation name
#             Column("name", String),
#             # Name and type of user participating in this conversation.
#             Column("user_name", String),
#             Column("user_type", String),
#             # True if this conversation is active.
#             Column("is_active", sqlite.BOOLEAN, default=True),
#             # -*- LLM data (name, model, etc.)
#             Column("llm", sqlite.JSON),
#             # -*- Conversation memory
#             Column("memory", sqlite.JSON),
#             # Metadata associated with this conversation.
#             Column("meta_data", sqlite.JSON),
#             # Extra data associated with this conversation.
#             Column("extra_data", sqlite.JSON),
#             # The timestamp of when this conversation was created.
#             Column("created_at", sqlite.DATETIME, default=current_datetime()),
#             # The timestamp of when this conversation was last updated.
#             Column("updated_at", sqlite.DATETIME, onupdate=current_datetime()),
#             extend_existing=True,
#             sqlite_autoincrement=True,
#         )
#
#     def table_exists(self) -> bool:
#         logger.debug(f"Checking if table exists: {self.table.name}")
#         try:
#             return inspect(self.db_engine).has_table(self.table.name)
#         except Exception as e:
#             logger.error(e)
#             return False
#
#     def create(self) -> None:
#         if not self.table_exists():
#             logger.debug(f"Creating table: {self.table.name}")
#             self.table.create(self.db_engine)
#
#     def _read(self, session: Session, conversation_id: str) -> Optional[Row[Any]]:
#         stmt = select(self.table).where(self.table.c.id == conversation_id)
#         try:
#             return session.execute(stmt).first()
#         except OperationalError:
#             # Create table if it does not exist
#             self.create()
#         except Exception as e:
#             logger.warning(e)
#         return None
#
#     def read(self, conversation_id: str) -> Optional[ConversationRow]:
#         with self.Session() as sess:
#             existing_row: Optional[Row[Any]] = self._read(session=sess, conversation_id=conversation_id)
#             return ConversationRow.model_validate(existing_row) if existing_row is not None else None
#
#     def get_all_conversation_ids(self, user_name: Optional[str] = None) -> List[str]:
#         conversation_ids: List[str] = []
#         try:
#             with self.Session() as sess:
#                 # get all conversation ids for this user
#                 stmt = select(self.table)
#                 if user_name is not None:
#                     stmt = stmt.where(self.table.c.user_name == user_name)
#                 # order by created_at desc
#                 stmt = stmt.order_by(self.table.c.created_at.desc())
#                 # execute query
#                 rows = sess.execute(stmt).fetchall()
#                 for row in rows:
#                     if row is not None and row.id is not None:
#                         conversation_ids.append(row.id)
#         except OperationalError:
#             logger.debug(f"Table does not exist: {self.table.name}")
#             pass
#         return conversation_ids
#
#     def get_all_conversations(self, user_name: Optional[str] = None) -> List[ConversationRow]:
#         conversations: List[ConversationRow] = []
#         try:
#             with self.Session() as sess:
#                 # get all conversation ids for this user
#                 stmt = select(self.table)
#                 if user_name is not None:
#                     stmt = stmt.where(self.table.c.user_name == user_name)
#                 # order by created_at desc
#                 stmt = stmt.order_by(self.table.c.created_at.desc())
#                 # execute query
#                 rows = sess.execute(stmt).fetchall()
#                 for row in rows:
#                     if row.id is not None:
#                         conversations.append(ConversationRow.model_validate(row))
#         except OperationalError:
#             logger.debug(f"Table does not exist: {self.table.name}")
#             pass
#         return conversations
#
#     def upsert(self, conversation: ConversationRow) -> Optional[ConversationRow]:
#         """
#         Create a new conversation if it does not exist, otherwise update the existing conversation.
#         """
#         with self.Session() as sess:
#             # Create an insert statement
#             stmt = sqlite.insert(self.table).values(
#                 id=conversation.id,
#                 name=conversation.name,
#                 user_name=conversation.user_name,
#                 user_type=conversation.user_type,
#                 is_active=conversation.is_active,
#                 llm=conversation.llm,
#                 memory=conversation.memory,
#                 meta_data=conversation.meta_data,
#                 extra_data=conversation.extra_data,
#             )
#
#             # Define the upsert if the id already exists
#             # See: https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#insert-on-conflict-upsert
#             stmt = stmt.on_conflict_do_update(
#                 index_elements=["id"],
#                 set_=dict(
#                     name=conversation.name,
#                     user_name=conversation.user_name,
#                     user_type=conversation.user_type,
#                     is_active=conversation.is_active,
#                     llm=conversation.llm,
#                     memory=conversation.memory,
#                     meta_data=conversation.meta_data,
#                     extra_data=conversation.extra_data,
#                 ),  # The updated value for each column
#             )
#
#             try:
#                 sess.execute(stmt)
#             except OperationalError:
#                 # Create table if it does not exist
#                 self.create()
#                 sess.execute(stmt)
#         return self.read(conversation_id=conversation.id)
#
#     def end(self, conversation_id: str) -> None:
#         with self.Session() as sess:
#             # Check if conversation exists in the database
#             existing_row: Optional[Row[Any]] = self._read(session=sess, conversation_id=conversation_id)
#             # If conversation exists, set is_active to False
#             if existing_row is not None:
#                 stmt = self.table.update().where(self.table.c.id == conversation_id).values(is_active=False)
#                 sess.execute(stmt)
#             sess.commit()
#
#     def delete(self) -> None:
#         if self.table_exists():
#             logger.debug(f"Deleting table: {self.table_name}")
#             self.table.drop(self.db_engine)
