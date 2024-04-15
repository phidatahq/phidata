from phi.assistant import Assistant
from phi.llm.openai import OpenAIChat

assistant = Assistant(llm=OpenAIChat(model="gpt-4-turbo"))

# Single Image
assistant.print_response(
    [
        {"type": "text", "text": "What's in this image, describe in 1 sentence"},
        {
            "type": "image_url",
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg",
        },
    ]
)

# Multiple Images
assistant.print_response(
    [
        {
            "type": "text",
            "text": "Is there any difference between these. Describe them in 1 sentence.",
        },
        {
            "type": "image_url",
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg",
        },
        {
            "type": "image_url",
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg",
        },
    ],
    markdown=True,
)
