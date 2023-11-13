from enum import Enum


class WorkspaceStarterTemplate(str, Enum):
    llm_app = "llm-app"
    llm_api = "llm-api"
    django_app = "django-app"
    streamlit_app = "streamlit-app"
    de_llm = "data-engineering-llm"
