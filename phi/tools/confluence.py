from phi.tools import Toolkit
from phi.utils.log import logger
from typing import Optional
from os import getenv
import json 

try:
    from atlassian import Confluence
except ImportError:
    raise ImportError("atlassian-python-api not install . Please install using `pip install atlassian-python-api`")


class ConfluenceTools(Toolkit):
    def __init__(
            self,
            username:str=None,
            password:str=None,
            url:str=None,
            api_key:Optional[str]=None,
            ):
        
        super().__init__(name="confluence_tools")
        self.url = url or getenv("CONFLUENCE_URL")
        self.username = username or getenv("CONFLUENCE_USERNAME")
        self.password=api_key or getenv("CONFLUENCE_API_KEY") or password

        if not self.url:
            logger.error("Confluence  url not provoided , either pass it in the constructor  or set CONFLUENCE_URL in environment variable")

        if not self.username:
            logger.error("Confluence username not provided , either pass it in the constructor or ser CONFLUENCE_USERNAME in environment variable")

        if not self.api_key:
            logger.error("CONFLUENCE API KEY not provided , nor password is provided ")
        
        self.client=Confluence(url=url,username=username,password=self.password)

    def get_page_content(self, space_key:str ,page_title:str ,expand:Optional[str]="body.storage"):

        try:
            page=self.confluence.get_page_by_title(space_key,page_title,expand=expand):
            if page:
                return json.dumps(page)
            
            logger.warning(f"Page '{page_title}' not found in space key '{space_key}'")
            return json.dumps({"error": f"Page '{page_title}' not found in space key'{space_key}'"})

        except Exception as e:
            logger.error(f"Error retrieving page '{page_title}': {e}")

            return json.dumps({"error": str(e)})
    

    def get_space_key(self,space_name:str):

        spaces=self.confluence.get_all_spaces()
        for space in spaces:
            if space['name'] == space_name:
                return space['key']
    
    def create_page(self,space_key:str,page_name:str):
        pass

    


            

