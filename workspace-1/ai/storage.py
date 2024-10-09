from phi.storage.assistant.postgres import PgAssistantStorage

from db.session import db_url

pdf_assistant_storage = PgAssistantStorage(
    db_url=db_url,
    table_name="pdf_assistant",
)

image_assistant_storage = PgAssistantStorage(
    db_url=db_url,
    table_name="image_assistant",
)

website_assistant_storage = PgAssistantStorage(
    db_url=db_url,
    table_name="website_assistant",
)
