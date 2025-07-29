import threading
from typing import Any, Protocol, Set, TypedDict

import streamlit as st
import websocket
from streamlit.runtime.scriptrunner_utils.script_run_context import add_script_run_ctx


# --- Protocols for callbacks ---


class OnMessage(Protocol):
    def __call__(self, ws: websocket.WebSocket, message: str) -> None:
        ...


class OnError(Protocol):
    def __call__(self, ws: websocket.WebSocket, error: Any) -> None:
        ...


class OnClose(Protocol):
    def __call__(
        self, ws: websocket.WebSocket, close_status_code: int, close_msg: str
    ) -> None:
        ...


class OnOpen(Protocol):
    def __call__(self, ws: websocket.WebSocket) -> None:
        ...


class GetWsUrl(Protocol):
    def __call__(self) -> str:
        ...


# --- Config type ---


class WebSocketAppConfig(TypedDict):
    on_message: OnMessage
    on_error: OnError
    on_close: OnClose
    on_open: OnOpen
    get_ws_url: GetWsUrl
    state_requirements: Set[str]


# --- Config factory ---


def get_config(
    on_message: OnMessage,
    on_error: OnError,
    on_close: OnClose,
    on_open: OnOpen,
    get_ws_url: GetWsUrl,
    state_requirements: Set[str],
) -> WebSocketAppConfig:
    """
    Create a WebSocketAppConfig with the provided parameters.
    This function is used to configure the WebSocket application with the necessary callbacks and URL retrieval function.

    Args:
        on_message (on_message_type): Callback function for handling incoming messages.
        on_error (on_error_type): Callback function for handling errors.
        on_close (on_close_type): Callback function for handling WebSocket closure.
        on_open (on_open_type): Callback function for handling WebSocket opening.
        get_ws_url (get_ws_url_type): Function to retrieve the WebSocket URL.
        state_requirements (state_requirements_type): Set of state keys that must be present before
            starting the WebSocket thread.
    Returns:
        WebSocketAppConfig: A configuration object for the WebSocket application.
    """
    return WebSocketAppConfig(
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
        on_open=on_open,
        get_ws_url=get_ws_url,
        state_requirements=state_requirements,
    )


# --- Worker starter ---


def start_ws_worker(ws_config: WebSocketAppConfig) -> None:
    for k in ["ws_app", "ws_thread"]:
        if k not in st.session_state:
            st.session_state[k] = None

    def ws_worker() -> None:
        try:
            ws = websocket.WebSocketApp(
                ws_config["get_ws_url"](),
                on_open=ws_config["on_open"],
                on_message=ws_config["on_message"],
                on_error=ws_config["on_error"],
                on_close=ws_config["on_close"],
            )
            st.session_state.ws_app = ws
            ws.run_forever()
        except Exception as e:
            st.error(f"WebSocket worker crashed: {e}")

    state_ready_to_start_thread: bool = all(
        st.session_state.get(key) for key in ws_config["state_requirements"]
    )
    thread_not_alive: bool = (
        st.session_state.ws_thread is None or not st.session_state.ws_thread.is_alive()
    )
    should_start_thread: bool = state_ready_to_start_thread and thread_not_alive
    if should_start_thread:
        ws_thread = threading.Thread(target=ws_worker, daemon=True)
        add_script_run_ctx(ws_thread)
        ws_thread.start()
        st.session_state.ws_thread = ws_thread
