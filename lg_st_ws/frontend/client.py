import datetime
import json
from zoneinfo import ZoneInfo, available_timezones

import streamlit as st
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage

from lg_st_ws.common.config import BOT_NAME
from lg_st_ws.common.models import (
    ChatMessage,
    SystemEvent,
    SystemEventMessage,
)
from lg_st_ws.frontend.ws import start_ws_worker

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "user_list" not in st.session_state:
    st.session_state.user_list = []
if "ws_app" not in st.session_state:
    st.session_state.ws_app = None
if "ws_thread" not in st.session_state:
    st.session_state.ws_thread = None
if "chat_active" not in st.session_state:
    st.session_state.chat_active = False
if "thread_id" not in st.session_state:
    st.session_state.thread_id = ""
if "username" not in st.session_state:
    st.session_state.username = ""


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
        submitted = st.form_submit_button("Start Chatting", disabled=chat_active)

    if submitted and thread_id and username:
        st.session_state.thread_id = thread_id
        st.session_state.username = username
        st.session_state.chat_active = True
        st.rerun()

    # # Use session_state values moving forward
    # thread_id = st.session_state.get("thread_id", "")
    # username = st.session_state.get("username", "")

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

    if st.sidebar.button("Disconnect WebSocket", disabled=not chat_active):
        reset_session()


@st.fragment(run_every=chat_update_interval)
def display_output():
    if st.session_state.user_list:

        def render_user(user):
            if user == st.session_state.username:
                return f"<span style='color:blue'>{user}</span>"
            elif user == BOT_NAME:
                return f"<span style='color:green'>{user}</span>"
            else:
                return user

        users = (render_user(user) for user in st.session_state.user_list + [BOT_NAME])
        st.markdown(f"**Connected users:** {', '.join(users)}", unsafe_allow_html=True)
        for msg in st.session_state.chat_history:
            local_tz = ZoneInfo(user_timezone)
            # LangChain chat message
            if isinstance(msg, BaseMessage):
                if isinstance(msg, AIMessage):
                    md = msg.response_metadata
                    role = "ai"
                elif isinstance(msg, HumanMessage):
                    md = msg.metadata
                    role = "human"
                else:
                    raise ValueError
                content = msg.content
                username = md["username"]
                timestamp = md["timestamp"]
                local_timestamp = datetime.datetime.fromisoformat(timestamp).astimezone(
                    local_tz
                )
                time_str = local_timestamp.strftime("%Y-%m-%d %I:%M:%S %p %Z")
                st.chat_message(role).markdown(
                    f"**{username}** [{time_str}]: {content}"
                )
            # System event message
            elif isinstance(msg, SystemEventMessage):
                local_timestamp = msg.timestamp.astimezone(local_tz)
                time_str = local_timestamp.strftime("%Y-%m-%d %I:%M:%S %p %Z")
                # Example: color for errors
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
            else:
                st.markdown(str(msg))


def display_input():
    if st.session_state.chat_active and st.session_state.ws_app:
        user_input = st.chat_input()
        if user_input:
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
            st.session_state.ws_app.send(json.dumps(chat_msg.jsonable_dump()))


start_ws_worker()

display_output()

display_input()
