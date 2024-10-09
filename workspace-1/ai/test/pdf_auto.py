from ai.assistants.pdf_auto import get_autonomous_pdf_assistant

auto_pdf_assistant = get_autonomous_pdf_assistant()

LOAD_KNOWLEDGE_BASE = True
if LOAD_KNOWLEDGE_BASE and auto_pdf_assistant.knowledge_base:
    auto_pdf_assistant.knowledge_base.load(recreate=False)

auto_pdf_assistant.print_response("Tell me about food safety?")
auto_pdf_assistant.print_response("How do I make chicken curry?")
auto_pdf_assistant.print_response("Summarize our conversation")
