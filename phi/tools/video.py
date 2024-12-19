from phi.tools import Toolkit
from moviepy import VideoFileClip, TextClip, CompositeVideoClip  # type: ignore
from openai import OpenAI

client = OpenAI()


class VideoTools(Toolkit):
    """Tool for processing video files, extracting audio, transcribing and adding captions"""

    def __init__(
        self,
        process_video: bool = True,
        transcribe_audio: bool = True,
        generate_captions: bool = True,
        embed_captions: bool = True,
    ):
        super().__init__(name="video_tools")

        if process_video:
            self.register(self.extract_audio)
        if transcribe_audio:
            self.register(self.transcribe_audio)
        if generate_captions:
            self.register(self.create_srt)
        if embed_captions:
            self.register(self.embed_captions)

    def extract_audio(self, video_path: str, output_path: str) -> str:
        """Converts video to audio using MoviePy

        Args:
            video_path: Path to the video file
            output_path: Path where the audio will be saved

        Returns:
            str: Path to the extracted audio file
        """
        try:
            video = VideoFileClip(video_path)
            video.audio.write_audiofile(output_path)
            print(f"Audio extracted to {output_path}")
            return output_path
        except Exception as e:
            return f"Failed to extract audio: {str(e)}"

    def transcribe_audio(self, audio_path: str) -> str:
        """Transcribe audio file using OpenAI's Whisper API

        Args:
            audio_path: Path to the audio file

        Returns:
            str: Transcribed text
        """
        print(f"Transcribing audio from {audio_path}")
        try:
            with open(audio_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1", file=audio_file, response_format="text"
                )
                print(f"Transcript: {transcript}")
            return transcript
        except Exception as e:
            return f"Failed to transcribe audio: {str(e)}"

    def create_srt(self, transcription: str, output_path: str) -> str:
        """Convert transcription to SRT format

        Args:
            transcription: Text transcription
            output_path: Path where the SRT file will be saved

        Returns:
            str: Path to the created SRT file
        """
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(f"1\n00:00:00,000 --> 99:59:59,999\n{transcription.strip()}\n\n")
            return output_path
        except Exception as e:
            return f"Failed to create SRT file: {str(e)}"

    def embed_captions(self, video_path: str, caption_path: str, output_path: str) -> str:
        """Embed captions into video using moviepy

        Args:
            video_path: Path to the video file
            caption_path: Path to the caption file
            output_path: Path where the captioned video will be saved

        Returns:
            str: Path to the output video with captions
        """
        try:
            # Load the video
            video = VideoFileClip(video_path)

            # Read captions from SRT file
            with open(caption_path, "r", encoding="utf-8") as f:
                caption_text = f.read().split("\n")[2]  # Get the text from SRT format

                # Create text clip using modern MoviePy syntax

                txt_clip = (
                    TextClip(
                        text=caption_text,
                        font_size=24,
                        color="white",
                        bg_color="black",
                        font="Arial.ttf",
                    )
                    .with_duration(video.duration)
                    .with_position(("center", "bottom"))
                )

            # Combine video and text using composition
            final_video = CompositeVideoClip([video, txt_clip])

            # Write the result
            final_video.write_videofile(output_path, codec="libx264", audio_codec="aac")

            # Clean up
            video.close()
            txt_clip.close()
            final_video.close()

            return output_path

        except Exception as e:
            print(f"Detailed error: {str(e)}")
            return f"Failed to embed captions: {str(e)}"
