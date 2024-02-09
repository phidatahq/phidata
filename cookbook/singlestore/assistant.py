# from os import getenv
# from typing import Optional
#
# from phi.assistant import Assistant
# from phi.knowledge import AssistantKnowledge
# from phi.llm.ollama import Ollama
# from phi.vectordb.singlestore import S2VectorDb
# from phi.storage.assistant.postgres import PgAssistantStorage
#
# from resources import config  # type: ignore
#
# host = getenv("SINGLESTORE_HOST", config["host"])
# port = getenv("SINGLESTORE_PORT", config["port"])
# username = getenv("SINGLESTORE_USERNAME", config["username"])
# password = getenv("SINGLESTORE_PASSWORD", config["password"])
# database = getenv("SINGLESTORE_DATABASE", config["database"])
# ssl_ca = getenv("SINGLESTORE_SSL_CA", config["ssl_ca"])
#
# db_url = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}?ssl_ca={ssl_ca}&ssl_verify_cert=true"
#
# assistant_storage = PgAssistantStorage(
#     db_url=db_url,
#     table_name="pdf_assistant",
# )
#
#
# def get_knowledge_base_for_model(model: str) -> AssistantKnowledge:
#     return AssistantKnowledge(
#         vector_db=S2VectorDb(collection="pdf_documents", schema="phidata", db_url=db_url),
#         num_documents=5,
#     )
#
#
# def get_local_rag_assistant(
#     model: str = "openhermes",
#     user_id: Optional[str] = None,
#     run_id: Optional[str] = None,
#     debug_mode: bool = False,
# ) -> Assistant:
#     """Get a Local RAG Assistant."""
#
#     return Assistant(
#         name="local_rag_assistant",
#         run_id=run_id,
#         user_id=user_id,
#         llm=Ollama(model=model),
#         storage=assistant_storage,
#         knowledge_base=get_knowledge_base_for_model(model),
#         # This setting adds references from the knowledge_base to the user prompt
#         add_references_to_prompt=True,
#         # This setting adds the last 4 messages from the chat history to the API call
#         add_chat_history_to_messages=True,
#         num_history_messages=4,
#         # This setting tells the LLM to format messages in markdown
#         markdown=True,
#         debug_mode=debug_mode,
#         description="You are a AI called 'Phi' designed to help users answer questions from a knowledge base of PDFs.",
#         assistant_data={"assistant_type": "rag"},
#     )
