import os
import requests
import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# Constants
TYPEFULLY_API_URL = "https://api.typefully.com/v1/drafts/"
TYPEFULLY_API_KEY = os.getenv("TYPEFULLY_API_KEY")
HEADERS = {
    "X-API-KEY": f"Bearer {TYPEFULLY_API_KEY}"
}


def json_to_typefully_content(thread_json: Dict[str, Any]) -> str:
    """Convert JSON thread format to Typefully's format with 4 newlines between tweets."""
    tweets = thread_json['tweets']
    formatted_tweets = []
    for tweet in tweets:
        tweet_text = tweet['content']
        if 'media_urls' in tweet and tweet['media_urls']:
            tweet_text += f"\n{tweet['media_urls'][0]}"
        formatted_tweets.append(tweet_text)

    return '\n\n\n\n'.join(formatted_tweets)


def json_to_linkedin_content(thread_json: Dict[str, Any]) -> str:
    """Convert JSON thread format to Typefully's format."""
    content = thread_json['content']
    if 'url' in thread_json and thread_json['url']:
        content += f"\n{thread_json['url']}"
    return content


def schedule_thread(
        content: str,
        schedule_date: str = "next-free-slot",
        threadify: bool = False,
        share: bool = False,
        auto_retweet_enabled: bool = False,
        auto_plug_enabled: bool = False
) -> Optional[Dict[str, Any]]:
    """Schedule a thread on Typefully."""
    payload = {
        "content": content,
        "schedule-date": schedule_date,
        "threadify": threadify,
        "share": share,
        "auto_retweet_enabled": auto_retweet_enabled,
        "auto_plug_enabled": auto_plug_enabled
    }

    payload = {key: value for key, value in payload.items() if value is not None}

    try:
        response = requests.post(TYPEFULLY_API_URL, json=payload, headers=HEADERS)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None


def schedule(
        thread_model: BaseModel,
        hours_from_now: int = 1,
        threadify: bool = False,
        share: bool = True,
        post_type: str = "twitter"
) -> Optional[Dict[str, Any]]:
    """
    Schedule a thread from a Pydantic model.

    Args:
        thread_model: Pydantic model containing thread data
        hours_from_now: Hours from now to schedule the thread (default: 1)
        threadify: Whether to let Typefully split the content (default: False)
        share: Whether to get a share URL in response (default: True)

    Returns:
        API response dictionary or None if failed
    """
    try:
        thread_content = ""
        # Convert Pydantic model to dict
        thread_json = thread_model.model_dump()
        print("######## Thread JSON: ", thread_json)
        # Convert to Typefully format
        if post_type == "twitter":
            thread_content = json_to_typefully_content(thread_json)
        elif post_type == "linkedin":
            thread_content = json_to_linkedin_content(thread_json)

        # Calculate schedule time
        schedule_date = (datetime.datetime.utcnow() +
                         datetime.timedelta(hours=hours_from_now)).isoformat() + "Z"

        if thread_content:
            # Schedule the thread
            response = schedule_thread(
                content=thread_content,
                schedule_date=schedule_date,
                threadify=threadify,
                share=share
            )

            if response:
                print("Thread scheduled successfully!")
                return response
            else:
                print("Failed to schedule the thread.")
                return None
        return None

    except Exception as e:
        print(f"Error: {str(e)}")
        return None
