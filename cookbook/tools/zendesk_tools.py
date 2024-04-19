from phi.assistant import Assistant
from phi.tools.zendesk import ZendeskTools
import os

# Retrieve Zendesk credentials from environment variables
zd_username = os.getenv("ZENDESK_USERNAME")
zd_password = os.getenv("ZENDESK_PW")
zd_company_name = os.getenv("ZENDESK_COMPANY_NAME")

if not zd_username or not zd_password or not zd_company_name:
    raise EnvironmentError(
        "Please set the following environment variables: ZENDESK_USERNAME, ZENDESK_PW, ZENDESK_COMPANY_NAME"
    )

# Initialize the ZendeskTools with the credentials
zendesk_tools = ZendeskTools(username=zd_username, password=zd_password, company_name=zd_company_name)

# Create an instance of Assistant and pass the initialized tool
assistant = Assistant(tools=[zendesk_tools], show_tool_calls=True)
assistant.print_response("How do I login?", markdown=True)
