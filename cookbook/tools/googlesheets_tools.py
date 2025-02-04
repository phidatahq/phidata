from agno.agent import Agent
from agno.tools.googlesheets import GoogleSheetsTools

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SAMPLE_SPREADSHEET_ID = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
SAMPLE_RANGE_NAME = "Class Data!A2:E"

google_sheets_tools = GoogleSheetsTools(
    spreadsheet_id=SAMPLE_SPREADSHEET_ID,
    spreadsheet_range=SAMPLE_RANGE_NAME,
    scopes=SCOPES,
)

agent = Agent(
    tools=[google_sheets_tools],
    instructions=[
        "You help users interact with Google Sheets through the API",
        "Before asking for spreadsheet details, first attempt the operation as the user may have already configured the ID and range in the constructor",
    ],
)
agent.print_response("Please tell me about the contents of the spreadsheet")
