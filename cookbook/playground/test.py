from phi.agent import Agent
from phi.model.groq import Groq
from phi.model.google import Gemini
from phi.playground import Playground, serve_playground_app
import os


def get_model(is_reasoning=False, is_groq=False):
    if is_groq:
        return Groq(
            id="llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY"),
        )
    else:
        return Gemini(
            id=(
                "gemini-2.0-flash-thinking-exp-1219"
                if is_reasoning
                else "gemini-2.0-flash-exp"
            ),
            api_key=os.getenv("GEMINI_API_KEY"),
        )


general_agent = Agent(
    name="General Agent",
    model=get_model(is_groq=True),
    markdown=True,
    debug_mode=True,
)


app = Playground(
    agents=[
        general_agent,
    ],
    workflows=[],
).get_app(
    use_async=False
)  # use_async should be false if gemini model is being used.

if __name__ == "__main__":
    serve_playground_app("agents:app", reload=True)
