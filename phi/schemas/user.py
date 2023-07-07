from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from phiterm.enums.user import UserPermissions


class UserSchema(BaseModel):
    """
    Schema used for user login and registration.
    """

    email: str
    id_user: Optional[int] = None
    handle: Optional[str] = None
    is_active: Optional[bool] = True
    is_admin: Optional[bool] = False
    is_bot: Optional[bool] = False
    is_test: Optional[bool] = False
    name: Optional[str] = None
    locale: Optional[str] = None
    country_code: Optional[str] = None
    tos_accepted: Optional[bool] = False
    email_verified: Optional[bool] = False
    user_permissions: Optional[List[UserPermissions]] = None

    @classmethod
    def from_dict(cls, user_dict: Dict[str, Any]):
        return cls(
            email=user_dict.get("email"),
            id_user=user_dict.get("id_user"),
            handle=user_dict.get("handle"),
            is_active=user_dict.get("is_active"),
            is_admin=user_dict.get("is_admin"),
            is_bot=user_dict.get("is_bot"),
            is_test=user_dict.get("is_test"),
            name=user_dict.get("name"),
            locale=user_dict.get("locale"),
            country_code=user_dict.get("country_code"),
            tos_accepted=user_dict.get("tos_accepted"),
            email_verified=user_dict.get("email_verified"),
            user_permissions=user_dict.get("user_permissions"),
        )


class EmailPasswordSignInSchema(BaseModel):
    email: str
    password: str
    auth_source: str = "cli"
