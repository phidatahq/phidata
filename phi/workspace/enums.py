from enum import Enum


class WorkspaceStarterTemplate(str, Enum):
    api_app = "api-app"
    llm_app = "llm-app"
    django_app = "django-app"
    streamlit_app = "streamlit-app"
    data_platform = "data-platform"
