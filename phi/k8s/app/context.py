from typing import Dict, Optional

from pydantic import BaseModel


class K8sBuildContext(BaseModel):
    namespace: str = "default"
    context: Optional[str] = None
    service_account_name: Optional[str] = None
    labels: Optional[Dict[str, str]] = None
