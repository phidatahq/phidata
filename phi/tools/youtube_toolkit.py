from urllib.parse import urlparse, parse_qs

from phi.tools import Toolkit
from phi.utils.log import logger

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    raise ImportError("`youtube_transcript_api` not installed. Please install using `pip install youtube_transcript_api`")


class YouTubeToolkit(Toolkit):
    def __init__(
        self,
    ):
        super().__init__(name="youtube_toolkit")

        self.register(self.get_video_captions)

    def get_video_captions(self, url: str) -> str:
        """
        Gets the captions of a YouTube video.

        Args:
            url: The URL of the YouTube video.
        
        Returns:
            The captions of the YouTube video.
        """
        if not url:
            return "No URL provided"

        try:
            video_id = self._get_youtube_video_id(url)
        except Exception:
            return "Error getting video ID for URL"

        try:
            captions = YouTubeTranscriptApi.get_transcript(video_id)
            logger.debug(f"Captions for video {video_id}: {captions}")
            if captions:
                return " ".join(line["text"] for line in captions)
            return "No captions found for video"
        except Exception:
            return "Error getting captions for video"

    def _get_youtube_video_id(self, url):
        """
        Internal function to get the video ID from a YouTube URL.

        Args:
            url: The URL of the YouTube video.
        
        Returns:
            The video ID of the YouTube video.
        """
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname

        if hostname == "youtu.be":
            return parsed_url.path[1:]
        if hostname in ("www.youtube.com", "youtube.com"):
            if parsed_url.path == "/watch":
                query_params = parse_qs(parsed_url.query)
                return query_params.get("v", [None])[0]
            if parsed_url.path.startswith("/embed/"):
                return parsed_url.path.split("/")[2]
            if parsed_url.path.startswith("/v/"):
                return parsed_url.path.split("/")[2]
        return None
