from typing import Any, Dict, List, Optional
from phi.tools.tool import Tool
from phi.utils.log import logger

try:
    from browser_use import BrowserUse
except ImportError:
    logger.error("Please install browser-use: pip install browser-use")
    BrowserUse = None


class BrowserUseTool:
    def __init__(
        self,
        ollama_base_url: str = "http://localhost:11434",
        model: str = "llama3.1",
        **kwargs: Any,
    ):
        if BrowserUse is None:
            raise ImportError("Please install browser-use: pip install browser-use")
        
        self.browser = BrowserUse(
            llm_base_url=ollama_base_url,
            llm_model=model,
            **kwargs
        )

    async def browse_website(self, url: str, task: str) -> str:
        """Browse a website and perform actions using browser automation.

        Args:
            url (str): URL of the website to browse
            task (str): Task to perform on the website

        Returns:
            str: Result of the browser automation task
        """
        try:
            result = await self.browser.browse(url=url, task=task)
            return str(result)
        except Exception as e:
            logger.error(f"Error during browser automation: {str(e)}")
            return f"Failed to perform task: {str(e)}"

    async def extract_website_info(self, url: str, query: str) -> str:
        """Extract information from a website using browser automation.

        Args:
            url (str): URL of the website to extract information from
            query (str): Information to extract

        Returns:
            str: Extracted information
        """
        try:
            result = await self.browser.extract(url=url, query=query)
            return str(result)
        except Exception as e:
            logger.error(f"Error during information extraction: {str(e)}")
            return f"Failed to extract information: {str(e)}"


def get_browser_use_tools(
    ollama_base_url: str = "http://localhost:11434",
    model: str = "llama3.1",
    browser_use_kwargs: Optional[Dict[str, Any]] = None,
) -> List[Tool]:
    """Get tools for browser automation using browser-use

    Args:
        ollama_base_url (str): Base URL for Ollama API
        model (str): Model to use for Ollama
        browser_use_kwargs (Dict[str, Any], optional): Additional kwargs for BrowserUse

    Returns:
        List[Tool]: List of browser automation tools
    """
    if BrowserUse is None:
        return []

    browser_use_kwargs = browser_use_kwargs or {}
    browser_tool = BrowserUseTool(
        ollama_base_url=ollama_base_url,
        model=model,
        **browser_use_kwargs
    )

    return [
        Tool(
            type="function",
            function={
                "name": "browse_website",
                "description": "Browse a website and perform actions using browser automation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL of the website to browse",
                        },
                        "task": {
                            "type": "string",
                            "description": "Task to perform on the website (e.g., 'click login button', 'fill form')",
                        },
                    },
                    "required": ["url", "task"],
                },
                "implementation": browser_tool.browse_website,
            },
        ),
        Tool(
            type="function",
            function={
                "name": "extract_website_info",
                "description": "Extract information from a website using browser automation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL of the website to extract information from",
                        },
                        "query": {
                            "type": "string",
                            "description": "Information to extract (e.g., 'product price', 'article content')",
                        },
                    },
                    "required": ["url", "query"],
                },
                "implementation": browser_tool.extract_website_info,
            },
        ),
    ] 