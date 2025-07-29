import datetime
from typing import Any

from langchain_core.messages import BaseMessage, messages_to_dict, messages_from_dict

from lg_st_ws.common.config import STRFTIME_FORMAT


def utc_dt_to_local_dt(
    utc_dt: datetime.datetime,
    local_tz: datetime.tzinfo,
) -> datetime.datetime:
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=datetime.UTC)
    return utc_dt.astimezone(local_tz)


def utc_str_to_local_str(utc_str: str, local_tz: datetime.tzinfo) -> str:
    utc_dt = datetime.datetime.fromisoformat(utc_str).astimezone(datetime.UTC)
    local_dt = utc_dt_to_local_dt(utc_dt, local_tz)
    return local_dt.strftime(STRFTIME_FORMAT)


def utc_dt_to_local_str(utc_dt: datetime.datetime, local_tz: datetime.tzinfo) -> str:
    local_dt = utc_dt_to_local_dt(utc_dt, local_tz)
    return local_dt.strftime(STRFTIME_FORMAT)


def serialize_history(history: list[BaseMessage]) -> list[dict[str, Any]]:
    """Serialize a list of LangChain messages to list of dicts."""
    return messages_to_dict(history)


def deserialize_history(serialized: list[dict[str, Any]]) -> list[BaseMessage]:
    """Deserialize a list of dicts to LangChain message objects."""
    return messages_from_dict(serialized)
