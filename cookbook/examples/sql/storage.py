from phi.storage.assistant.postgres import PgAssistantStorage

from db.session import db_url

nyc_storage = PgAssistantStorage(
    schema="ai",
    db_url=db_url,
    table_name="nyc_assistant",
)
