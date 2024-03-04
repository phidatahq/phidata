from typing import List, Dict, Optional

from phi.prompt.template import PromptTemplate
from phi.utils.log import logger


class PromptRegistry:
    def __init__(self, name: str, templates: Optional[List[PromptTemplate]] = None):
        if name is None:
            raise ValueError("PromptRegistry must have a name.")

        self.name: str = name
        self.prompts: Dict[str, PromptTemplate] = {}
        if templates:
            for template in templates:
                if template.id is None:
                    raise ValueError("PromptTemplate cannot be registered without an id.")
                self.register(template.id, template)
        logger.debug(f"Initialized prompt registry: {name}")
        self.load_registry_from_api()

    def register(self, id: str, prompt: PromptTemplate):
        self.prompts[id] = prompt
        # register_with_api(self.name, id, prompt)
        logger.debug(f"Registered prompt: {id}")

    def get(self, id: str) -> Optional[PromptTemplate]:
        logger.debug(f"Getting prompt: {id}")
        return self.prompts.get(id, None)

    def load_registry_from_api(self):
        logger.debug(f"Loading prompt registry from phidata: {self.name}")

    def refresh(self):
        self.load_registry_from_api()

    def __getitem__(self, id) -> Optional[PromptTemplate]:
        return self.get(id)
