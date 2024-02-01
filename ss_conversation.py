import typer
from rich.prompt import Prompt
from typing import Optional, List

from phi.utils.log import set_log_level_to_debug
from phi.assistant import Assistant
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.singlestore.s2vectordb import singlestore
from phi.storage.assistant.singlestore import SingleStoreAssistantStorage

set_log_level_to_debug()

ss_db_url = (
    "mysql+pymysql://admin:Single!123"
    "@svc-107a6beb-b33f-4490-8429-c7a2d74f16db-dml.aws-virginia-3.svc.singlestore.com:3306/"
    "?ssl_ca=/Users/vishwajeetdabholkar/Downloads/singlestore_bundle.pem"
)


knowledge_base = PDFUrlKnowledgeBase(
    urls=[
        "https://www.family-action.org.uk/content/uploads/2019/07/meals-more-recipes.pdf"
    ],
    vector_db=singlestore(
        collection="recipes",
        db_url=ss_db_url,
    ),
)
knowledge_base.load(recreate=False)

storage = SingleStoreAssistantStorage(
    table_name="recipe_conversations",
    db_url=ss_db_url,
)

# print("done")
# Assistant1 = Assistant(
#     debug_mode=True,
#     knowledge_base=knowledge_base,
#     storage=storage,
#     add_references_to_prompt=True,
# )

# Assistant1.print_response("Tell me a 2 sentence horror story.")


def llm_app(new: bool = False, user: str = "user"):
    conversation_id: Optional[str] = None

    if not new:
        existing_conversation_ids: List[str] = storage.get_all_run_ids(user)
        if len(existing_conversation_ids) > 0:
            conversation_id = existing_conversation_ids[0]

    conversation = Assistant(
        run_id=run_id,
        user_id=user,
        user_name=user,
        run_id=run_id,
        user_id=user,
        knowledge_base=knowledge_base,
        storage=storage,
        
        # add_references_to_prompt=True,
        function_calls=True,
        show_function_calls=True,
    )

    # conversation.knowledge_base.load(recreate=False)
    print(f"Conversation ID: {conversation.run_id}\n")
    while True:
        message = Prompt.ask(f"[bold] :sunglasses: {user} [/bold]")
        if message in ("exit", "bye"):
            break
        conversation.print_response(message)


if __name__ == "__main__":
    typer.run(llm_app)
