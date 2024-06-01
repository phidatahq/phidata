from enum import Enum


class WorkspaceStarterTemplate(str, Enum):
    ai_app = "ai-app"
    ai_api = "ai-api"
    django_app = "django-app"
    streamlit_app = "streamlit-app"
    llm_os = "llm-os"
    agentic_rag = "personalized-agentic-rag"
