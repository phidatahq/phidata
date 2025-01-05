from phi.agent import Agent
from phi.tools.postgres import PostgresTools

db_name = "ai"
user = "ai"
password = "ai"
host = "localhost"
port = 5532

agent = Agent(
    tools=[
        PostgresTools(db_name=db_name, user=user, password=password, host=host, port=port),
    ]
)
agent.print_response("List the tables in the database", markdown=True)
