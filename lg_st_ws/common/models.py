import datetime
from enum import StrEnum
from typing import Any, Annotated

from fastapi.encoders import jsonable_encoder
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.messages import (
    BaseMessage,
    messages_from_dict,
    message_to_dict,
    messages_to_dict,
)
from langgraph.graph import add_messages
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


# --- Protocol enums ---


class RoleType(StrEnum):
    user = "user"
    ai = "ai"
    system = "system"


class MessageType(StrEnum):
    chat = "chat"
    handshake = "handshake"
    system_event = "system_event"
    user_list = "user_list"
    message_history = "message_history"


class SystemEvent(StrEnum):
    user_joined = "user_joined"
    user_left = "user_left"
    error = "error"
    ws_closed = "ws_closed"
    ws_error = "ws_error"
    exception = "exception"


# --- Protocol envelope models ---


class JSONModel(BaseModel):
    def jsonable_dump(self, *args, **kwargs):
        """Return a JSON-serializable representation of the model."""
        return jsonable_encoder(self.model_dump(*args, **kwargs))


class HandshakeMessage(JSONModel):
    type: MessageType = MessageType.handshake
    username: str


class SystemEventMessage(JSONModel):
    type: MessageType = MessageType.system_event
    event: SystemEvent
    thread_id: str
    username: str
    content: str
    timestamp: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )


class UserListMessage(JSONModel):
    type: MessageType = MessageType.user_list
    thread_id: str
    users: list[str]
    timestamp: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )


class MessageHistory(JSONModel):
    type: MessageType = MessageType.message_history
    thread_id: str
    messages: list[dict[str, Any]]  # serialized LangChain messages
    timestamp: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )


class ChatMessage(JSONModel):
    type: MessageType = MessageType.chat
    thread_id: str
    message: dict[str, Any]  # serialized LangChain message
    timestamp: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )

    @staticmethod
    def from_lc_message(
        thread_id: str, msg: BaseMessage, timestamp: datetime.datetime | None = None
    ) -> "ChatMessage":
        return ChatMessage(
            thread_id=thread_id,
            message=message_to_dict(msg),
            timestamp=timestamp or datetime.datetime.now(datetime.UTC),
        )

    def to_lc_message(self) -> BaseMessage:
        return messages_from_dict([self.message])[0]


# --- Utility functions ---


def serialize_history(history: list[BaseMessage]) -> list[dict[str, Any]]:
    """Serialize a list of LangChain messages to list of dicts."""
    return messages_to_dict(history)


def deserialize_history(serialized: list[dict[str, Any]]) -> list[BaseMessage]:
    """Deserialize a list of dicts to LangChain message objects."""
    return messages_from_dict(serialized)


class GraphState(TypedDict):
    messages: Annotated[list[HumanMessage | AIMessage | BaseMessage], add_messages]
