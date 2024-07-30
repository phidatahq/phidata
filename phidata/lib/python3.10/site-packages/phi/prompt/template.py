from typing import Optional, Dict, Any
from collections import defaultdict

from pydantic import BaseModel, ConfigDict
from phi.utils.log import logger


class PromptTemplate(BaseModel):
    id: Optional[str] = None
    template: str
    default_params: Optional[Dict[str, Any]] = None
    ignore_missing_keys: bool = False
    default_factory: Optional[Any] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def get_prompt(self, **kwargs) -> str:
        template_params = (self.default_factory or defaultdict(str)) if self.ignore_missing_keys else {}
        if self.default_params:
            template_params.update(self.default_params)
        template_params.update(kwargs)

        try:
            return self.template.format_map(template_params)
        except KeyError as e:
            logger.error(f"Missing template parameter: {e}")
            raise
