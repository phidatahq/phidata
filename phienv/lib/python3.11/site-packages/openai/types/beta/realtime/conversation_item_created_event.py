# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing_extensions import Literal

from ...._models import BaseModel
from .conversation_item import ConversationItem

__all__ = ["ConversationItemCreatedEvent"]


class ConversationItemCreatedEvent(BaseModel):
    event_id: str
    """The unique ID of the server event."""

    item: ConversationItem
    """The item to add to the conversation."""

    previous_item_id: str
    """
    The ID of the preceding item in the Conversation context, allows the client to
    understand the order of the conversation.
    """

    type: Literal["conversation.item.created"]
    """The event type, must be `conversation.item.created`."""
