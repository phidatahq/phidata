from phidata.app.assistant import Assistant

from workspace.settings import ws_settings

#
# -*- Assistant Docker resources
#

dev_assistant = Assistant(
    runtime=ws_settings.dev_env,
    enabled=ws_settings.dev_assistant_enabled,
    ws_settings=ws_settings,
    container_host_port=9090,
)
