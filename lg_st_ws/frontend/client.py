import datetime
from zoneinfo import ZoneInfo, available_timezones

import streamlit as st
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage

from lg_st_ws.common.config import BOT_NAME
from lg_st_ws.common.models import (
    ChatMessage,
    SystemEvent,
    SystemEventMessage,
)
from lg_st_ws.common.util import utc_str_to_local_str, utc_dt_to_local_str
from lg_st_ws.frontend.ws_impl import start_ws_worker_impl

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "user_list" not in st.session_state:
    st.session_state.user_list = []
if "ws_app" not in st.session_state:
    st.session_state.ws_app = None
if "ws_thread" not in st.session_state:
    st.session_state.ws_thread = None
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "username" not in st.session_state:
    st.session_state.username = None
if "chat_active" not in st.session_state:
    st.session_state.chat_active = False


def reset_session():
    if st.session_state.ws_app is not None:
        st.session_state.ws_app.close()
    st.session_state.ws_app = None
    st.session_state.ws_thread = None
    st.session_state.chat_history = []
    st.session_state.user_list = []
    st.session_state.thread_id = ""
    st.session_state.username = ""
    st.session_state.chat_active = False
    st.rerun()


@st.cache_data()
def get_available_timezones() -> list[str]:
    """Return a list of available timezones."""
    return sorted(available_timezones())


with st.sidebar:
    st.header("Chat Settings")
    chat_active = st.session_state.get("chat_active", False)

    with st.form("chat_form"):
        thread_id = st.text_input(
            "Thread ID", max_chars=20, key="thread_id_input", disabled=chat_active
        )
        username = st.text_input(
            "Username", max_chars=20, key="username_input", disabled=chat_active
        )
        submitted = st.form_submit_button("Connect", disabled=chat_active)

    if submitted and thread_id and username:
        st.session_state.thread_id = thread_id
        st.session_state.username = username
        st.session_state.chat_active = True
        st.rerun()

    user_timezone = st.selectbox(
        "Select Your Timezone",
        options=get_available_timezones(),
        index=get_available_timezones().index("UTC"),
    )

    chat_update_interval = st.number_input(
        "Chat Update Interval (seconds)",
        min_value=1,
        max_value=60,
        value=2,
        step=1,
    )

    st.sidebar.button("Disconnect", disabled=not chat_active, on_click=reset_session)


local_tz = ZoneInfo(user_timezone)


def display_user_list():
    """Format the user list for display.
    Order: current user (blue), bot (green), then other users sorted alphabetically.
    """
    if st.session_state.user_list:
        _users = sorted(
            user
            for user in st.session_state.user_list
            if user not in (st.session_state.username, BOT_NAME)
        )
        _users.insert(0, f"<span style='color:blue'>{st.session_state.username}</span>")
        _users.insert(1, f"<span style='color:green'>{BOT_NAME}</span>")
        users_str = ", ".join(_users)
        st.markdown(f"**Connected users:** {users_str}", unsafe_allow_html=True)


def display_lc_message(msg: BaseMessage):
    if isinstance(msg, AIMessage):
        md = msg.response_metadata
        role = "ai"
    elif isinstance(msg, HumanMessage):
        md = msg.metadata
        role = "human"
    else:
        raise ValueError(f"Unsupported message type: {type(msg)}")

    content = msg.content
    username = md["username"]
    timestamp = md["timestamp"]

    time_str = utc_str_to_local_str(timestamp, local_tz)
    st.chat_message(role).markdown(f"**{username}** [{time_str}]: {content}")


def display_se_message(msg: SystemEventMessage):
    time_str = utc_dt_to_local_str(msg.timestamp, local_tz)
    if msg.event == SystemEvent.error:
        st.markdown(
            f"<span style='color:red'>*{msg.content}*</span>  \n<small>{time_str}</small>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"*{msg.content}*  \n<small>{time_str}</small>",
            unsafe_allow_html=True,
        )


def display_other(msg: str):
    st.markdown(msg)


@st.fragment(run_every=chat_update_interval)
def display_output():
    display_user_list()

    for msg in st.session_state.chat_history:
        if isinstance(msg, BaseMessage):
            display_lc_message(msg)
        elif isinstance(msg, SystemEventMessage):
            display_se_message(msg)
        else:
            display_other(msg)


def send_user_input(user_input: str):
    user_message = HumanMessage(
        content=user_input,
        metadata={
            "username": st.session_state.username,
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
        },
    )
    chat_msg = ChatMessage.from_lc_message(
        thread_id=st.session_state.thread_id,
        msg=user_message,
    )
    st.session_state.ws_app.send(chat_msg.jsonable_dump_json())


def display_input():
    if st.session_state.chat_active and st.session_state.ws_app:
        user_input = st.chat_input()
        if user_input:
            send_user_input(user_input)


start_ws_worker_impl()

display_output()

display_input()
