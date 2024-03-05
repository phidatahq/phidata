from typing import List, Dict, Optional

from phi.api.prompt import sync_prompt_registry_api, sync_prompt_template_api
from phi.api.schemas.prompt import (
    PromptRegistrySync,
    PromptTemplatesSync,
    PromptTemplateSync,
    PromptRegistrySchema,
    PromptTemplateSchema,
)
from phi.prompt.template import PromptTemplate
from phi.utils.log import logger


class PromptRegistry:
    def __init__(self, name: str, templates: Optional[List[PromptTemplate]] = None, sync: bool = True):
        if name is None:
            raise ValueError("PromptRegistry must have a name.")

        self.name: str = name
        self.prompts: Dict[str, PromptTemplate] = {}
        # Add templates to prompts
        if templates:
            for template in templates:
                if template.id is None:
                    raise ValueError("PromptTemplate cannot be added to Registry without an id.")
                self.prompts[template.id] = template

        # If the registry should sync with phidata
        self._sync = sync
        self._remote_registry: Optional[PromptRegistrySchema] = None
        self._remote_templates: Optional[Dict[str, PromptTemplateSchema]] = None
        # Sync the registry with phidata
        if self._sync:
            self.sync_registry()
        logger.debug(f"Initialized prompt registry: {name}")

    def add(self, prompt: PromptTemplate):
        prompt_id = prompt.id
        if prompt_id is None:
            raise ValueError("PromptTemplate cannot be added to Registry without an id.")

        self.prompts[prompt_id] = prompt
        if self._sync:
            self.sync_template(prompt_id, prompt)
        logger.debug(f"Added prompt: {prompt_id}")

    def get(self, id: str) -> Optional[PromptTemplate]:
        logger.debug(f"Getting prompt: {id}")
        return self.prompts.get(id, None)

    def sync_registry(self):
        logger.debug(f"Syncing registry with phidata: {self.name}")
        self._remote_registry, self._remote_templates = sync_prompt_registry_api(
            registry=PromptRegistrySync(registry_name=self.name),
            templates=PromptTemplatesSync(
                templates={
                    k: PromptTemplateSync(template_id=k, template_data=v.model_dump(exclude_none=True))
                    for k, v in self.prompts.items()
                }
            ),
        )
        if self._remote_templates is not None:
            for k, v in self._remote_templates.items():
                self.prompts[k] = PromptTemplate.model_validate(v.template_data)
        logger.debug(f"Synced registry with phidata: {self.name}")

    def sync_template(self, id: str, prompt: PromptTemplate):
        logger.debug(f"Syncing template: {id} with registry: {self.name}")
        if self._remote_templates is not None and id in self._remote_templates:
            if self._remote_templates[id].template_data != prompt.model_dump(exclude_none=True):
                _prompt_template: PromptTemplateSchema = sync_prompt_template_api(
                    registry=PromptRegistrySync(registry_name=self.name),
                    prompt_template=PromptTemplateSync(
                        template_id=id, template_data=prompt.model_dump(exclude_none=True)
                    ),
                )
                self._remote_templates[id] = _prompt_template
        else:
            _prompt_template: PromptTemplateSchema = sync_prompt_template_api(
                registry=PromptRegistrySync(registry_name=self.name),
                prompt_template=PromptTemplateSync(template_id=id, template_data=prompt.model_dump(exclude_none=True)),
            )
            if self._remote_templates is None:
                self._remote_templates = {}
            self._remote_templates[id] = _prompt_template

    def __getitem__(self, id) -> Optional[PromptTemplate]:
        return self.get(id)

    def __str__(self):
        return f"PromptRegistry: {self.name}"

    def __repr__(self):
        return f"PromptRegistry: {self.name}"
