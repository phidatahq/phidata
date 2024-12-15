import time
from pathlib import Path

from phi.agent import Agent
from phi.model.google import Gemini
from google.generativeai import upload_file, get_file

agent = Agent(
    model=Gemini(id="gemini-2.0-flash-exp"),
    markdown=True,
)

# Please download "GreatRedSpot.mp4" using
# wget https://storage.googleapis.com/generativeai-downloads/images/GreatRedSpot.mp4
video_path = Path(__file__).parent.joinpath("GreatRedSpot.mp4")
video_file = upload_file(video_path)
# Check whether the file is ready to be used.
while video_file.state.name == "PROCESSING":
    time.sleep(2)
    video_file = get_file(video_file.name)

print(f"Uploaded video: {video_file}")

agent.print_response("Tell me about this video", videos=[video_file], stream=True)
