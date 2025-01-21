"""🎨 AI Image Reporter - Your Visual Analysis & News Companion!

This example shows how to create an AI agent that can analyze images and connect
them with current events using web searches. Perfect for:
1. News reporting and journalism
2. Travel and tourism content
3. Social media analysis
4. Educational presentations
5. Event coverage

Example images to try:
- Famous landmarks (Eiffel Tower, Taj Mahal, etc.)
- City skylines
- Cultural events and festivals
- Breaking news scenes
- Historical locations

Run `pip install duckduckgo-search agno` to install dependencies.
"""

from agno.agent import Agent
from agno.media import Image
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    description=(
        "You are a world-class visual journalist and cultural correspondent with a gift "
        "for bringing images to life through storytelling! 📸✨ With the observational skills "
        "of a detective and the narrative flair of a bestselling author, you transform visual "
        "analysis into compelling stories that inform and captivate."
    ),
    instructions=(
        "When analyzing images and reporting news, follow these principles:\n\n"
        "1. Visual Analysis:\n"
        "   - Start with an attention-grabbing headline using relevant emoji\n"
        "   - Break down key visual elements with expert precision\n"
        "   - Notice subtle details others might miss\n"
        "   - Connect visual elements to broader contexts\n\n"
        "2. News Integration:\n"
        "   - Research and verify current events related to the image\n"
        "   - Connect historical context with present-day significance\n"
        "   - Prioritize accuracy while maintaining engagement\n"
        "   - Include relevant statistics or data when available\n\n"
        "3. Storytelling Style:\n"
        "   - Maintain a professional yet engaging tone\n"
        "   - Use vivid, descriptive language\n"
        "   - Include cultural and historical references when relevant\n"
        "   - End with a memorable sign-off that fits the story\n\n"
        "4. Reporting Guidelines:\n"
        "   - Keep responses concise but informative (2-3 paragraphs)\n"
        "   - Balance facts with human interest\n"
        "   - Maintain journalistic integrity\n"
        "   - Credit sources when citing specific information\n\n"
        "Transform every image into a compelling news story that informs and inspires!"
    ),
    tools=[DuckDuckGoTools()],
    show_tool_calls=True,
    markdown=True,
)

# Example usage with a famous landmark
agent.print_response(
    "Tell me about this image and share the latest relevant news.",
    images=[
        Image(
            url="https://upload.wikimedia.org/wikipedia/commons/0/0c/GoldenGateBridge-001.jpg"
        )
    ],
    stream=True,
)

# More examples to try:
"""
Sample prompts to explore:
1. "What's the historical significance of this location?"
2. "How has this place changed over time?"
3. "What cultural events happen here?"
4. "What's the architectural style and influence?"
5. "What recent developments affect this area?"

Sample image URLs to analyze:
1. Eiffel Tower: "https://upload.wikimedia.org/wikipedia/commons/8/85/Tour_Eiffel_Wikimedia_Commons_%28cropped%29.jpg"
2. Taj Mahal: "https://upload.wikimedia.org/wikipedia/commons/b/bd/Taj_Mahal%2C_Agra%2C_India_edit3.jpg"
3. Golden Gate Bridge: "https://upload.wikimedia.org/wikipedia/commons/0/0c/GoldenGateBridge-001.jpg"
"""

# To get the response in a variable:
# from rich.pretty import pprint
# response = agent.run(
#     "Analyze this landmark's architecture and recent news.",
#     images=[Image(url="YOUR_IMAGE_URL")],
# )
# pprint(response.content)
