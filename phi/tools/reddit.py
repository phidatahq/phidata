import json
from os import getenv
from typing import Optional, Dict, List, Union
from phi.tools import Toolkit
from phi.utils.log import logger

try:
    import praw  # type: ignore
except ImportError:
    raise ImportError("`praw` not installed.")


class RedditTools(Toolkit):
    reddit: Optional[praw.Reddit]

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        user_agent: Optional[str] = None,
        get_user_info: bool = True,
        get_top_posts: bool = True,
        get_subreddit_info: bool = True,
        get_trending_subreddits: bool = True,
        get_subreddit_stats: bool = True,
    ):
        super().__init__(name="reddit")

        self.client_id = client_id or getenv("REDDIT_CLIENT_ID")
        self.client_secret = client_secret or getenv("REDDIT_CLIENT_SECRET")
        self.user_agent = user_agent or getenv("REDDIT_USER_AGENT", "RedditTools v1.0")

        self.reddit = None
        if all([self.client_id, self.client_secret]):
            self.reddit = praw.Reddit(
                client_id=self.client_id, client_secret=self.client_secret, user_agent=self.user_agent
            )
        else:
            logger.warning("Missing Reddit API credentials")

        if get_user_info:
            self.register(self.get_user_info)
        if get_top_posts:
            self.register(self.get_top_posts)
        if get_subreddit_info:
            self.register(self.get_subreddit_info)
        if get_trending_subreddits:
            self.register(self.get_trending_subreddits)
        if get_subreddit_stats:
            self.register(self.get_subreddit_stats)

    def get_user_info(self, username: str) -> str:
        """Get information about a Reddit user."""
        if not self.reddit:
            return "Please provide Reddit API credentials"

        try:
            logger.info(f"Getting info for u/{username}")

            user = self.reddit.redditor(username)
            info: Dict[str, Union[str, int, bool, float]] = {
                "name": user.name,
                "comment_karma": user.comment_karma,
                "link_karma": user.link_karma,
                "is_mod": user.is_mod,
                "is_gold": user.is_gold,
                "is_employee": user.is_employee,
                "created_utc": user.created_utc,
            }

            return json.dumps(info)

        except Exception as e:
            return f"Error getting user info: {e}"

    def get_top_posts(self, subreddit: str, time_filter: str = "week", limit: int = 10) -> str:
        """
        Get top posts from a subreddit for a specific time period.

        Args:
            subreddit (str): Name of the subreddit.
            time_filter (str): Time period to filter posts.
            limit (int): Number of posts to fetch.

        Returns:
            str: JSON string containing top posts.
        """
        if not self.reddit:
            return "Please provide Reddit API credentials"

        try:
            posts = self.reddit.subreddit(subreddit).top(time_filter=time_filter, limit=limit)
            top_posts: List[Dict[str, Union[str, int, float]]] = [
                {
                    "title": post.title,
                    "score": post.score,
                    "url": post.url,
                    "author": str(post.author),
                    "created_utc": post.created_utc,
                }
                for post in posts
            ]
            return json.dumps({"top_posts": top_posts})
        except Exception as e:
            return f"Error getting top posts: {e}"

    def get_subreddit_info(self, subreddit_name: str) -> str:
        """
        Get information about a specific subreddit.

        Args:
            subreddit_name (str): Name of the subreddit.

        Returns:
            str: JSON string containing subreddit information.
        """
        if not self.reddit:
            return "Please provide Reddit API credentials"

        try:
            logger.info(f"Getting info for r/{subreddit_name}")

            subreddit = self.reddit.subreddit(subreddit_name)
            info: Dict[str, Union[str, int, bool, float]] = {
                "display_name": subreddit.display_name,
                "title": subreddit.title,
                "description": subreddit.description,
                "subscribers": subreddit.subscribers,
                "created_utc": subreddit.created_utc,
                "over18": subreddit.over18,
                "public_description": subreddit.public_description,
                "url": subreddit.url,
            }

            return json.dumps(info)

        except Exception as e:
            return f"Error getting subreddit info: {e}"

    def get_trending_subreddits(self) -> str:
        """Get currently trending subreddits."""
        if not self.reddit:
            return "Please provide Reddit API credentials"

        try:
            popular_subreddits = self.reddit.subreddits.popular(limit=5)
            trending: List[str] = [subreddit.display_name for subreddit in popular_subreddits]
            return json.dumps({"trending_subreddits": trending})
        except Exception as e:
            return f"Error getting trending subreddits: {e}"

    def get_subreddit_stats(self, subreddit: str) -> str:
        """
        Get statistics about a subreddit.

        Args:
            subreddit (str): Name of the subreddit.

        Returns:
            str: JSON string containing subreddit statistics
        """
        if not self.reddit:
            return "Please provide Reddit API credentials"

        try:
            sub = self.reddit.subreddit(subreddit)
            stats: Dict[str, Union[str, int, bool, float]] = {
                "display_name": sub.display_name,
                "subscribers": sub.subscribers,
                "active_users": sub.active_user_count,
                "description": sub.description,
                "created_utc": sub.created_utc,
                "over18": sub.over18,
                "public_description": sub.public_description,
            }
            return json.dumps({"subreddit_stats": stats})
        except Exception as e:
            return f"Error getting subreddit stats: {e}"
