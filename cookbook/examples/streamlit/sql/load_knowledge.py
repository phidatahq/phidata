from agno.utils.log import logger
from sql_agent import agent_knowledge


def load_sql_agent_knowledge_base(recreate: bool = True):
    logger.info("Loading SQL agent knowledge.")
    agent_knowledge.load(recreate=recreate)
    logger.info("SQL agent knowledge loaded.")


if __name__ == "__main__":
    load_sql_agent_knowledge_base()
