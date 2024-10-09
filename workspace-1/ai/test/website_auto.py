from ai.assistants.website_auto import get_autonomous_website_assistant

auto_website_assistant = get_autonomous_website_assistant()

LOAD_KNOWLEDGE_BASE = True
if LOAD_KNOWLEDGE_BASE and auto_website_assistant.knowledge_base:
    auto_website_assistant.knowledge_base.load(recreate=False)

auto_website_assistant.print_response("What is phidata?")
auto_website_assistant.print_response("How do I build an AI App using phidata?")
