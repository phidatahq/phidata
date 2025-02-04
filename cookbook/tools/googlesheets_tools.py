"""
This script demonstrates how to use the GoogleSheetsTools class to interact with Google Sheets through an Agent.

Setup:

1: Follow the steps: https://developers.google.com/sheets/api/quickstart/python
2: Save the credentials.json file to the root of the project or update the path in the GoogleSheetsTools class
3: Run the script to authenticate and generate the token.json file. In the initial run, the script will open a browser window to authenticate the application.
4: Update the SCOPES as per the requirements of the application.

# Example spreadsheet: https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/
The ID is the URL of the spreadsheet and the range is the sheet name and the range of cells to read.
"""


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
        "You help users interact with Google Sheets using tools that use the Google Sheets API",
        "Before asking for spreadsheet details, first attempt the operation as the user may have already configured the ID and range in the constructor",
    ],
)
agent.print_response("Please tell me about the contents of the spreadsheet")
