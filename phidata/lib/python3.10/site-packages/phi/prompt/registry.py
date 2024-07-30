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
from phi.prompt.exceptions import PromptUpdateException, PromptNotFoundException
from phi.utils.log import logger


class PromptRegistry:
    def __init__(self, name: str, prompts: Optional[List[PromptTemplate]] = None, sync: bool = True):
        if name is None:
            raise ValueError("PromptRegistry must have a name.")

        self.name: str = name
        # Prompts initialized with the registry
        # NOTE: These prompts cannot be updated
        self.prompts: Dict[str, PromptTemplate] = {}
        # Add prompts to prompts
        if prompts:
            for _prompt in prompts:
                if _prompt.id is None:
                    raise ValueError("PromptTemplate cannot be added to Registry without an id.")
                self.prompts[_prompt.id] = _prompt

        # All prompts in the registry, including those synced from phidata
        self.all_prompts: Dict[str, PromptTemplate] = {}
        self.all_prompts.update(self.prompts)

        # If the registry should sync with phidata
        self._sync = sync
        self._remote_registry: Optional[PromptRegistrySchema] = None
        self._remote_templates: Optional[Dict[str, PromptTemplateSchema]] = None
        # Sync the registry with phidata
        if self._sync:
            self.sync_registry()
        logger.debug(f"Initialized prompt registry: {name}")

    def get(self, id: str) -> Optional[PromptTemplate]:
        logger.debug(f"Getting prompt: {id}")
        return self.all_prompts.get(id, None)

    def get_all(self) -> Dict[str, PromptTemplate]:
        return self.all_prompts

    def add(self, prompt: PromptTemplate):
        prompt_id = prompt.id
        if prompt_id is None:
            raise ValueError("PromptTemplate cannot be added to Registry without an id.")

        self.all_prompts[prompt_id] = prompt
        if self._sync:
            self._sync_template(prompt_id, prompt)
        logger.debug(f"Added prompt: {prompt_id}")

    def update(self, id: str, prompt: PromptTemplate, upsert: bool = True):
        # Check if the prompt exists in the initial registry and should not be updated
        if id in self.prompts:
            raise PromptUpdateException(f"Prompt Id: {id} cannot be updated as it is initialized with the registry.")
        # If upsert is False and the prompt is not found, raise an exception
        if not upsert and id not in self.all_prompts:
            raise PromptNotFoundException(f"Prompt Id: {id} not found in registry.")
        # Update or insert the prompt
        self.all_prompts[id] = prompt
        # Sync the template if sync is enabled
        if self._sync:
            self._sync_template(id, prompt)
        logger.debug(f"Updated prompt: {id}")

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
                self.all_prompts[k] = PromptTemplate.model_validate(v.template_data)
        logger.debug(f"Synced registry with phidata: {self.name}")

    def _sync_template(self, id: str, prompt: PromptTemplate):
        logger.debug(f"Syncing template: {id} with registry: {self.name}")

        # Determine if the template needs to be synced either because
        # remote templates are not available, or
        # template is not in remote templates, or
        # the template_data has changed.
        needs_sync = (
            self._remote_templates is None
            or id not in self._remote_templates
            or self._remote_templates[id].template_data != prompt.model_dump(exclude_none=True)
        )

        if needs_sync:
            _prompt_template: Optional[PromptTemplateSchema] = sync_prompt_template_api(
                registry=PromptRegistrySync(registry_name=self.name),
                prompt_template=PromptTemplateSync(template_id=id, template_data=prompt.model_dump(exclude_none=True)),
            )
            if _prompt_template is not None:
                if self._remote_templates is None:
                    self._remote_templates = {}
                self._remote_templates[id] = _prompt_template

    def __getitem__(self, id) -> Optional[PromptTemplate]:
        return self.get(id)

    def __str__(self):
        return f"PromptRegistry: {self.name}"

    def __repr__(self):
        return f"PromptRegistry: {self.name}"
