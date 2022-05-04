from typing import Optional

from pydantic import BaseModel


class PhidataBaseArgs(BaseModel):
    name: Optional[str] = None
    version: Optional[str] = None
    enabled: bool = True

    class Config:
        arbitrary_types_allowed = True


class PhidataBase:
    """Phidata Base Class"""

    def __init__(self) -> None:
        self.args: Optional[PhidataBaseArgs] = None

    @property
    def name(self) -> str:
        return (
            self.args.name
            if (self.args and self.args.name)
            else self.__class__.__name__
        )

    @property
    def version(self) -> Optional[str]:
        return self.args.version if self.args else None

    @property
    def enabled(self) -> bool:
        return self.args.enabled if self.args else False
