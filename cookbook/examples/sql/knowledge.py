from phi.knowledge.json import JSONKnowledgeBase
from phi.knowledge.text import TextKnowledgeBase
from phi.knowledge.combined import CombinedKnowledgeBase
from phi.vectordb.pgvector import PgVector2
from phi.utils.log import set_log_level_to_debug

from db.session import db_url
from workspace.settings import ws_settings
from utils.log import logger

nyc_text_knowledge_base = TextKnowledgeBase(
    path=ws_settings.ws_root.joinpath("nyc", "knowledge_base"),
    formats=[".txt", ".sql", ".md"],
)

nyc_json_knowledge_base = JSONKnowledgeBase(
    path=ws_settings.ws_root.joinpath("nyc", "knowledge_base"),
)

nyc_knowledge = CombinedKnowledgeBase(
    sources=[
        nyc_text_knowledge_base,
        nyc_json_knowledge_base,
    ],
    # Store this knowledge base in ai.nyc_knowledge
    vector_db=PgVector2(
        db_url=db_url,
        collection="nyc_knowledge",
    ),
    # 5 references are added to the prompt
    num_documents=5,
)


def load_nyc_knowledge_base() -> str:
    set_log_level_to_debug()

    logger.info("Loading NYC knowledge base.")
    nyc_knowledge.load(recreate=True)
