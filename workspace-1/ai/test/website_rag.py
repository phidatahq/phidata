from ai.assistants.website_rag import get_rag_website_assistant

rag_website_assistant = get_rag_website_assistant()

LOAD_KNOWLEDGE_BASE = True
if LOAD_KNOWLEDGE_BASE and rag_website_assistant.knowledge_base:
    rag_website_assistant.knowledge_base.load(recreate=False)

rag_website_assistant.print_response("What is phidata?")
rag_website_assistant.print_response("How do I build an AI App using phidata?")
