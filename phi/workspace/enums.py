from enum import Enum


class WorkspaceStarterTemplate(str, Enum):
    llm_app = "llm-app"
    api_app = "api-app"
    django_app = "django-app"
    streamlit_app = "streamlit-app"
    ai_platform = "ai-platform"
