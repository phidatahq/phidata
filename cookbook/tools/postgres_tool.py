from phi.agent import Agent
from phi.tools.postgres import PostgresTools

# Initialize PostgresTools with connection details
postgres_tools = PostgresTools(
    host="localhost",
    port=5532,
    db_name="ai",
    user="ai", 
    password="ai"
)

# Create an agent with the PostgresTools
agent = Agent(tools=[postgres_tools])

# Example: Ask the agent to run a SQL query
agent.print_response("""
Please run a SQL query to get all users from the users table 
who signed up in the last 30 days
""")
