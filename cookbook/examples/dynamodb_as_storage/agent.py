import typer
from typing import Optional, List
from phi.agent import Agent
from phi.storage.agent.dynamodb import DynamoDbAgentStorage

storage = DynamoDbAgentStorage(table_name="dynamo_agent", region_name="us-east-1")


def dynamodb_agent(new: bool = False, user: str = "user"):
    session_id: Optional[str] = None

    if not new:
        existing_sessions: List[str] = storage.get_all_session_ids(user)
        if len(existing_sessions) > 0:
            session_id = existing_sessions[0]

    agent = Agent(
        session_id=session_id,
        user_id=user,
        storage=storage,
        show_tool_calls=True,
        # Enable the agent to read the chat history
        read_chat_history=True,
        add_history_to_messages=True,
        debug_mode=True,
    )
    if session_id is None:
        session_id = agent.session_id
        print(f"Started Session: {session_id}\n")
    else:
        print(f"Continuing Session: {session_id}\n")

    # Runs the agent as a cli app
    agent.cli_app(markdown=True)


if __name__ == "__main__":
    typer.run(dynamodb_agent)
