from phi.utils.log import logger
from assistant import assistant_knowledge


def load_sql_assistant_knowledge_base(recreate: bool = True):
    logger.info("Loading SQL Assistant knowledge.")
    assistant_knowledge.load(recreate=recreate)
    logger.info("SQL Assistant knowledge loaded.")


if __name__ == "__main__":
    load_sql_assistant_knowledge_base()
