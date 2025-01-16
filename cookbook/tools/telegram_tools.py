from phi.agent import Agent
from phi.tools.telegram import TelegramTools


telegram_token = "<enter-your-bot-token>"
chat_id = "<enter-your-chat-id>"

agent = Agent(
    name="telegram",
    tools=[TelegramTools(token=telegram_token, chat_id=chat_id)],
)

agent.print_response("Send message to telegram chat a paragraph about the moon")
