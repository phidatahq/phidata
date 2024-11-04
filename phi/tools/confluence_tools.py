from phi.tools import Toolkit
from phi.utils.log import logger
from os import getenv


try:
    from atlassian import Confluence
except ImportError:
    raise ImportError("`atlassian` not installed.Please install it using `pip install atlassian-python-api`")


class ConfluenceTools(Toolkit):
    def __init__(self, url: str, username: str, api_token: str):
        super().__init__(name="confluence_tools")
        self.url = url or getenv("CONFLUENCE_URL")
        self.username = username or getenv("CONFLUENCE_USERNAME")
        self.api_token = api_token or getenv("CONFLUENCE_API_TOKEN")
        self.confluence = Confluence(
            url=self.url,
            username=self.username,
            password=self.api_token,
            cloud=True
        )
        self.register(self.get_page)
        self.register(self.create_page)
        self.register(self.get_page_by_id)
        self.register(self.update_page)
        self.register(self.delete_page)

    def get_page(self, space: str, title: str):
        """
        Get the list of pages in a space by title.

        Args:
            space (str): The space key of the space.
            title (str): The title of the page.

        Returns:
            dict: The page data.
        """
        try:
            if not space:
                logger.error("Space not provided")
                return None
            if not title:
                logger.error("Title not provided")
                return None
            return self.confluence.get_page_by_title(space, title)
        except Exception as e:
            logger.error(f"Error getting page: {e}")
            return None

    def create_page(self, space: str, title: str, content: str):
        """
        Create a new page in a space.

        Args:
            space (str): The space key of the space.
            title (str): The title of the page.
            content (str): The content of the page.

        Returns:
            dict: The page data.
        """
        try:
            if not space:
                logger.error("Space not provided")
                return None
            if not title:
                logger.error("Title not provided")
                return None
            if not content:
                logger.error("Content not provided")
                return None
            return self.confluence.create_page(space, title, content)
        except Exception as e:
            logger.error(f"Error creating page: {e}")
            return None

    def get_page_by_id(self, page_id: str):
        """
        Get a page by its id.

        Args:
            page_id (str): The id of the page.

        Returns:
            dict: The page data.
        """
        try:
            if not page_id:
                logger.error("Page id not provided")
                return None
            return self.confluence.get_page_by_id(page_id)
        except Exception as e:
            logger.error(f"Error getting page by id: {e}")
            return None

    def update_page(self, page_id: str, title: str, content: str):
        """
        Update a page by its id.

        Args:
            page_id (str): The id of the page.
            title (str): The title of the page.
            content (str): The content of the page.

        Returns:
            dict: The page data.
        """
        try:
            if not page_id:
                logger.error("Page id not provided")
                return None
            if not title:
                logger.error("Title not provided")
                return None
            if not content:
                logger.error("Content not provided")
                return None
            return self.confluence.update_page(page_id, title, content)
        except Exception as e:
            logger.error(f"Error updating page: {e}")
            return None

    def delete_page(self, page_id: str):
        """
        Delete a page by its id.

        Args:
            page_id (str): The id of the page.

        Returns:
            bool: True if the page is deleted, False otherwise.
        """
        try:
            if not page_id:
                logger.error("Page id not provided")
                return False
            return self.confluence.remove_page(page_id)
        except Exception as e:
            logger.error(f"Error deleting page: {e}")
            return False
