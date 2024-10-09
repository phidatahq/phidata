from ai.assistants.pdf_rag import get_rag_pdf_assistant

rag_pdf_assistant = get_rag_pdf_assistant()

LOAD_KNOWLEDGE_BASE = True
if LOAD_KNOWLEDGE_BASE and rag_pdf_assistant.knowledge_base:
    rag_pdf_assistant.knowledge_base.load(recreate=False)

rag_pdf_assistant.print_response("Tell me about food safety?")
rag_pdf_assistant.print_response("How do I make chicken curry?")
rag_pdf_assistant.print_response("Summarize our conversation")
