"""Please install dependencies using:
pip install openai moviepy ffmpeg
"""

from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.moviepy_video_tools import MoviePyVideoTools
from phi.tools.openai import OpenAITools


video_tools = MoviePyVideoTools(process_video=True, generate_captions=True, embed_captions=True)


openai_tools = OpenAITools()

video_caption_agent = Agent(
    name="Video Caption Generator Agent",
    model=OpenAIChat(
        id="gpt-4o",
    ),
    tools=[video_tools, openai_tools],
    description="You are an AI agent that can generate and embed captions for videos.",
    instructions=[
        "When a user provides a video, process it to generate captions.",
        "Use the video processing tools in this sequence:",
        "1. Extract audio from the video using extract_audio",
        "2. Transcribe the audio using transcribe_audio",
        "3. Generate SRT captions using create_srt",
        "4. Embed captions into the video using embed_captions",
    ],
    markdown=True,
)


video_caption_agent.print_response(
    "Generate captions for {video with location} and embed them in the video"
)
