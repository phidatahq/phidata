from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.video import VideoTools
import requests
from pathlib import Path

def download_video(url: str, output_path: str) -> str:
    """Download video from URL"""
    response = requests.get(url, stream=True)
    response.raise_for_status()

    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    return output_path

# Create a single tool instance instead of multiple ones
video_tools = VideoTools(
    process_video=True,
    transcribe_audio=True,
    generate_captions=True,
    embed_captions=True
)

# Define the tools schema for OpenAI


video_caption_agent = Agent(
    name="Video Caption Generator Agent",
    model=OpenAIChat(
        id="gpt-4o",

    ),
    tools=[video_tools],
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


    # video_url = "/home/yus-vengeance/Downloads/linkedin_motivation.mp4"

# Create temp directory if it doesn't exist
temp_dir = Path("/tmp/video_captions")
temp_dir.mkdir(parents=True, exist_ok=True)




video_caption_agent.print_response(
    "Generate captions for /home/yus-vengeance/Downloads/linkedin_motivation_with_captions.mp4 and embed them in the video"
)
