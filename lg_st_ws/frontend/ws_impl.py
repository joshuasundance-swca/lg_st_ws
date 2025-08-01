import datetime
import json
from typing import Any

import streamlit as st
import websocket

from lg_st_ws.common.config import WS_URL
from lg_st_ws.common.models import (
    MessageType,
    ChatMessage,
    SystemEventMessage,
    SystemEvent,
    UserListMessage,
    MessageHistory,
    HandshakeMessage,
)
from lg_st_ws.common.util import deserialize_history
from lg_st_ws.frontend.ws_protocol import get_config, start_ws_worker


def on_message(ws: websocket.WebSocket, message: str):
    try:
        data = json.loads(message)
        msg_type = data.get("type")
        if msg_type == MessageType.chat:
            incoming_chat_msg = ChatMessage(**data)
            lc_msg = incoming_chat_msg.to_lc_message()
            st.session_state.chat_history.append(lc_msg)
        elif msg_type == MessageType.system_event:
            sys_msg = SystemEventMessage(**data)
            st.session_state.chat_history.append(sys_msg)
            if sys_msg.event == SystemEvent.user_joined:
                if sys_msg.username not in st.session_state.user_list:
                    st.session_state.user_list.append(sys_msg.username)
            elif sys_msg.event == SystemEvent.user_left:
                if sys_msg.username in st.session_state.user_list:
                    st.session_state.user_list.remove(sys_msg.username)
        elif msg_type == MessageType.user_list:
            user_list_msg = UserListMessage(**data)
            st.session_state.user_list = user_list_msg.users
        elif msg_type == MessageType.message_history:
            history_msg = MessageHistory(**data)
            st.session_state.chat_history = deserialize_history(history_msg.messages)
        elif "error" in data:
            # Represent errors as a system event for the UI
            error_event = SystemEventMessage(
                type=MessageType.system_event,
                event=SystemEvent.error,
                thread_id=st.session_state.thread_id,
                username="system",
                content=f"Error: {data['error']}",
                timestamp=datetime.datetime.now(datetime.UTC),
            )
            st.session_state.chat_history.append(error_event)
    except Exception as e:
        error_event = SystemEventMessage(
            type=MessageType.system_event,
            event=SystemEvent.error,
            thread_id=st.session_state.thread_id,
            username="system",
            content=f"Error parsing message: {e}",
            timestamp=datetime.datetime.now(datetime.UTC),
        )
        st.session_state.chat_history.append(error_event)


def on_error(ws: websocket.WebSocket, error: Any):
    print(error)
    if isinstance(error, Exception):
        raise error
    # error_event = SystemEventMessage(
    #     type=MessageType.system_event,
    #     event=SystemEvent.error,
    #     thread_id=st.session_state.thread_id,
    #     username="system",
    #     content=f"WebSocket error: {error}",
    #     timestamp=datetime.datetime.now(datetime.UTC),
    # )
    # st.session_state.chat_history.append(error_event)


def on_close(ws: websocket.WebSocket, close_status_code, close_msg):
    close_event = SystemEventMessage(
        type=MessageType.system_event,
        event=SystemEvent.ws_closed,
        thread_id=st.session_state.thread_id,
        username="system",
        content="WebSocket closed.",
        timestamp=datetime.datetime.now(datetime.UTC),
    )
    st.session_state.chat_history.append(close_event)


def on_open(ws: websocket.WebSocket):
    handshake = HandshakeMessage(
        username=st.session_state.username,
    )
    ws.send(json.dumps(handshake.jsonable_dump()))


def get_ws_url() -> str:
    return WS_URL.format(thread_id=st.session_state.thread_id)


cfg = get_config(
    on_message=on_message,
    on_error=on_error,
    on_close=on_close,
    on_open=on_open,
    get_ws_url=get_ws_url,
    state_requirements={"thread_id", "username"},
)


def start_ws_worker_impl():
    start_ws_worker(cfg)
