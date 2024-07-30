from typing import Optional

from pydantic import BaseModel


class UserSchema(BaseModel):
    """Schema for user data returned by the API."""

    id_user: int
    email: Optional[str] = None
    username: Optional[str] = None
    is_active: Optional[bool] = True
    is_bot: Optional[bool] = False
    name: Optional[str] = None
    email_verified: Optional[bool] = False


class EmailPasswordAuthSchema(BaseModel):
    email: str
    password: str
    auth_source: str = "cli"
