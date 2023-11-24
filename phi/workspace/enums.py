from enum import Enum


class WorkspaceStarterTemplate(str, Enum):
    llm_app = "llm-app"
    llm_api = "llm-api"
    django_app = "django-app"
    streamlit_app = "streamlit-app"
    junior_de = "junior-de"
