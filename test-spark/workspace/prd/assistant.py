from phidata.app.assistant import Assistant

from workspace.settings import ws_settings

#
# -*- Assistant Kubernetes resources
#

prd_assistant = Assistant(
    runtime=ws_settings.prd_env,
    enabled=ws_settings.prd_assistant_enabled,
    ws_settings=ws_settings,
)
