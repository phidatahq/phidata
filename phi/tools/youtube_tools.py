import json
from urllib.parse import urlparse, parse_qs, urlencode
from urllib.request import urlopen
from typing import Optional, List

from phi.tools import Toolkit

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    raise ImportError(
        "`youtube_transcript_api` not installed. Please install using `pip install youtube_transcript_api`"
    )


class YouTubeTools(Toolkit):
    def __init__(
        self,
        get_video_captions: bool = True,
        get_video_data: bool = True,
        languages: Optional[List[str]] = None,
    ):
        super().__init__(name="youtube_tools")

        self.languages: Optional[List[str]] = languages
        if get_video_captions:
            self.register(self.get_youtube_video_captions)
        if get_video_data:
            self.register(self.get_youtube_video_data)

    def get_youtube_video_id(self, url: str) -> Optional[str]:
        """Function to get the video ID from a YouTube URL.

        Args:
            url: The URL of the YouTube video.

        Returns:
            str: The video ID of the YouTube video.
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

    def get_youtube_video_data(self, url: str) -> str:
        """Function to get video data from a YouTube URL.
        Data returned includes {title, author_name, author_url, type, height, width, version, provider_name, provider_url, thumbnail_url}

        Args:
            url: The URL of the YouTube video.

        Returns:
            str: JSON data of the YouTube video.
        """
        if not url:
            return "No URL provided"

        try:
            video_id = self.get_youtube_video_id(url)
        except Exception:
            return "Error getting video ID from URL, please provide a valid YouTube url"

        try:
            params = {"format": "json", "url": f"https://www.youtube.com/watch?v={video_id}"}
            url = "https://www.youtube.com/oembed"
            query_string = urlencode(params)
            url = url + "?" + query_string

            with urlopen(url) as response:
                response_text = response.read()
                video_data = json.loads(response_text.decode())
                clean_data = {
                    "title": video_data.get("title"),
                    "author_name": video_data.get("author_name"),
                    "author_url": video_data.get("author_url"),
                    "type": video_data.get("type"),
                    "height": video_data.get("height"),
                    "width": video_data.get("width"),
                    "version": video_data.get("version"),
                    "provider_name": video_data.get("provider_name"),
                    "provider_url": video_data.get("provider_url"),
                    "thumbnail_url": video_data.get("thumbnail_url"),
                }
                return json.dumps(clean_data, indent=4)
        except Exception as e:
            return f"Error getting video data: {e}"

    def get_youtube_video_captions(self, url: str) -> str:
        """Use this function to get captions from a YouTube video.

        Args:
            url: The URL of the YouTube video.

        Returns:
            str: The captions of the YouTube video.
        """
        if not url:
            return "No URL provided"

        try:
            video_id = self.get_youtube_video_id(url)
        except Exception:
            return "Error getting video ID from URL, please provide a valid YouTube url"

        try:
            captions = None
            if self.languages:
                captions = YouTubeTranscriptApi.get_transcript(video_id, languages=self.languages)
            else:
                captions = YouTubeTranscriptApi.get_transcript(video_id)
            # logger.debug(f"Captions for video {video_id}: {captions}")
            if captions:
                return " ".join(line["text"] for line in captions)
            return "No captions found for video"
        except Exception as e:
            return f"Error getting captions for video: {e}"
