import os
import json
from typing import Optional, List, Dict
from phi.tools import Toolkit
from phi.utils.log import logger

try:
    from atlassian import Confluence
except ImportError:
    raise ImportError("`atlassian-python-api` not installed. Please install using `pip install atlassian-python-api`")

class ConfluenceTools(Toolkit):
    def __init__(
        self, 
        server_url: Optional[str] = None, 
        username: Optional[str] = None, 
        password: Optional[str] = None, 
        api_token: Optional[str] = None
    ):
        """Initialize the Confluence toolkit.

        Args:
            server_url: URL of the Confluence server.
            username: Confluence username for authentication (if not using API token).
            password: Confluence password for authentication (if not using API token).
            api_token: API token for authentication (if not using username and password).
        
        Raises:
            ValueError: If the server URL or authentication credentials are not provided.
        """
        super().__init__(name="confluence")

        self.server_url = server_url or os.getenv("CONFLUENCE_SERVER_URL")
        self.username = username or os.getenv("CONFLUENCE_USERNAME")
        self.password = password or os.getenv("CONFLUENCE_API_TOKEN")

        if not self.server_url:
            logger.error("Confluence server URL not provided. Please set the CONFLUENCE_SERVER_URL environment variable.")
        
        if not self.username:
            logger.error("Confluence username not provided. Please set the CONFLUENCE_USERNAME environment variable.")
        
        if not self.password:
            logger.error("Confluence API token not provided. Please set the CONFLUENCE_API_TOKEN environment variable.")

    
        self.confluence = Confluence(
            url=self.server_url,
            username=self.username,
            password=self.password,
            cloud=True
        )

        # Register methods
        self.register(self.get_page)
        self.register(self.create_page)
        self.register(self.update_page)
        self.register(self.search_cql)

    def get_page(self, space: str, title: str, expand: Optional[str] = None) -> str:
        """Retrieve a Confluence page by its title.

        Args:
            space: The key of the space where the page is located.
            title: The title of the page to retrieve.
            expand: Optional additional fields to expand in the response.

        Returns:
            str: JSON representation of the page if found, or an error message.
        """
        try:
            page = self.confluence.get_page_by_title(space, title, expand=expand)
            if page:
                return json.dumps(page)
            logger.warning(f"Page '{title}' not found in space '{space}'")
            return json.dumps({"error": f"Page '{title}' not found in space '{space}'"})
        except Exception as e:
            logger.error(f"Error retrieving page '{title}': {e}")
            return json.dumps({"error": str(e)})


    def create_page(self, space: str, title: str, body: str, parent_id: Optional[str] = None) -> str:
        """Create a new page in Confluence.

        Args:
            space: The key of the space where the page will be created.
            title: The title of the new page.
            body: The content of the new page.
            parent_id: Optional ID of the parent page if creating a child page.

        Returns:
            str: JSON representation containing the ID and title of the created page or an error message.
        """
        try:
            page = self.confluence.create_page(space, title, body, parent_id=parent_id)
            logger.info(f"Page created: {title} with ID {page['id']}")
            return json.dumps({"id": page['id'], "title": title})
        except Exception as e:
            logger.error(f"Error creating page '{title}': {e}")
            return json.dumps({"error": str(e)})

    def update_page(self, page_id: str, title: str, body: str) -> str:
        """Update an existing Confluence page.

        Args:
            page_id: The ID of the page to update.
            title: The new title for the page.
            body: The updated content for the page.

        Returns:
            str: JSON representation containing the status and ID of the updated page or an error message.
        """
        try:
            updated_page = self.confluence.update_page(page_id, title, body)
            logger.info(f"Page updated: {title} with ID {updated_page['id']}")
            return json.dumps({"status": "success", "id": updated_page['id']})
        except Exception as e:
            logger.error(f"Error updating page '{title}': {e}")
            return json.dumps({"error": str(e)})

    def search_cql(self, cql: str, limit: int = 10) -> str:
        """Execute a CQL (Confluence Query Language) search.

        Args:
            cql: The CQL query string to execute.
            limit: Maximum number of results to return (default is 10).

        Returns:
            str: JSON representation of the search results or an error message.
        """
        try:
            results = self.confluence.cql(cql, limit=limit)
            logger.info(f"Found {len(results.get('results', []))} results for CQL '{cql}'")
            return json.dumps(results.get('results', []))
        except Exception as e:
            logger.error(f"Error executing CQL search '{cql}': {e}")
            return json.dumps({"error": str(e)})
