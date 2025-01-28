from agents import agent_knowledge
from agno.utils.log import logger


def load_knowledge(recreate: bool = True):
    logger.info("Loading Agent knowledge.")
    agent_knowledge.load(recreate=recreate)
    logger.info("Agent knowledge loaded.")


if __name__ == "__main__":
    load_knowledge()
