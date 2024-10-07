"""Run `pip install duckduckgo-search sqlalchemy openai` to install dependencies."""

from os import getenv

from sqlalchemy.engine import create_engine

from phi.agent import Agent
from phi.tools.duckduckgo import DuckDuckGo
from phi.storage.agent.singlestore import S2AgentStorage

# -*- SingleStore Configuration -*-
USERNAME = getenv("SINGLESTORE_USERNAME")
PASSWORD = getenv("SINGLESTORE_PASSWORD")
HOST = getenv("SINGLESTORE_HOST")
PORT = getenv("SINGLESTORE_PORT")
DATABASE = getenv("SINGLESTORE_DATABASE")
SSL_CERT = getenv("SINGLESTORE_SSL_CERT", None)

# -*- SingleStore DB URL
db_url = f"mysql+pymysql://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}?charset=utf8mb4"
if SSL_CERT:
    db_url += f"&ssl_ca={SSL_CERT}&ssl_verify_cert=true"

# -*- SingleStore DB Engine
db_engine = create_engine(db_url)

# Create an agent with SingleStore storage
agent = Agent(
    storage=S2AgentStorage(table_name="agent_runs", db_engine=db_engine, schema=DATABASE),
    tools=[DuckDuckGo()],
    add_history_to_messages=True,
)
agent.print_response("How many people live in Canada?")
agent.print_response("What is their national anthem called?")
