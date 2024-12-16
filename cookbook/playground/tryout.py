from phi.agent.agent import Agent
from phi.memory.agent import AgentMemory
from phi.memory.db.postgres import PgMemoryDb
from phi.model.ollama import Ollama
from phi.playground.playground import Playground
from phi.playground.serve import serve_playground_app

agent = Agent(
    name="Test",
    agent_id="test-agent",
    model=Ollama(id="llama3.1:8b"),
    memory=AgentMemory(
        db=PgMemoryDb(table_name="agent_memory", db_url="postgresql+psycopg://ai:ai@localhost:5532/ai"),
        create_user_memories=True,
        create_session_summary=True,
    ),
)

app = Playground(agents=[agent]).get_app()

if __name__ == "__main__":
    serve_playground_app("tryout:app", reload=True)
