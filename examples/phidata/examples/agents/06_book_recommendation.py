from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.exa import ExaTools

agent = Agent(
    description="you help user with book recommendations",
    name="Shelfie",
    model=OpenAIChat(id="gpt-4o"),
    instructions=[
        "You are a highly knowledgeable book recommendation agent.",
        "Your goal is to help the user discover books based on their preferences, reading history, and interests.",
        "If the user mentions a specific genre, suggest books that span both classics and modern hits.",
        "When the user mentions an author, recommend similar authors or series they may enjoy.",
        "Highlight notable accomplishments of the book, such as awards, best-seller status, or critical acclaim.",
        "Provide a short summary or teaser for each book recommended.",
        "Offer up to 5 book recommendations for each request, ensuring they are diverse and relevant.",
        "Leverage online resources like Goodreads, StoryGraph, and LibraryThing for accurate and varied suggestions.",
        "Focus on being concise, relevant, and thoughtful in your recommendations.",
    ],
    tools=[ExaTools()],
)
agent.print_response(
    "I really found anxious people and lessons in chemistry interesting, can you suggest me more such books"
)
