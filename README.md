# lg_st_ws

A **multi-user, real-time chat application** powered by FastAPI, Streamlit, WebSockets, and LangGraph, featuring an AI assistant (LLM) in every chat room.

![Chat Application Screenshot](./screenshot.png)

---

## Features

- **Multi-user chat rooms** (threads in LangGraph checkpoints) with real-time updates via WebSockets.
- **Bi-directional websockets** for low-latency communication.
  - **Broadcasting** to all users in a thread.
- **AI assistant** in every thread (OpenAI GPT-4.1 by default).
  - **Passive participation**, speaking only when spoken to.
- **Frontend**: Modern, interactive UI built with Streamlit.
  - **Multithreading** for real-time, bi-directional WebSocket communication.
  - `st.fragment` for efficient UI updates that don't block the main thread.
  - `st.session_state` used as a queue between the WebSocket thread and the Streamlit UI.
- **Backend**: FastAPI server orchestrating WebSockets, chat history, and LLM interactions.
- **Time zone support** for user-friendly timestamps.
- **User presence** and system event notifications.
- **Streamlit websocket abstraction** for the benefit of other Streamlit devs <3

---

## Quick Start

- `OPENAI_API_KEY` in `.env`
- Other environment variables in `docker-compose.yml`
- `docker compose up`
- `http://localhost:8001`

---

## But why though?

This project serves as a practical example of integrating modern web technologies to create a real-time, interactive chat application. It showcases:
- The power of **WebSockets** for real-time communication.
- The flexibility of **FastAPI** for building asynchronous web applications.
- The ease of use of **Streamlit** for creating interactive web UIs.
  - The novel use of multithreading in Streamlit solves many common issues with real-time updates in web applications.
- The capabilities of **LangGraph** for orchestrating complex, persistent workflows with LLMs.

And, more importantly, because it's
* fun
* reminiscent of IRC, a classic protocol for real-time chat
* a way to make better Streamlit apps with persistent, bi-directional websockets 😉

---

## Guide: Using the Multithreaded Streamlit + WebSocket Setup
This guide walks you through integrating a robust, multithreaded WebSocket client into your Streamlit app, using the provided configuration and worker utilities. This pattern is ideal for chat apps, collaborative tools, dashboards, or any real-time feature in Streamlit.

### 1. Overview
The setup consists of:

- **Config Factory** (`get_config`): Collects all callbacks, URL logic, and requirements into a single config object.
- **Worker Starter** (`start_ws_worker`): Manages a background thread for the WebSocket connection, ensuring Streamlit’s session state is respected and thread-safe.
- **Callback Protocols**: Type-safe signatures for message, error, open, and close handlers.

### 2. Step-by-Step Usage

#### Step 1: Define Your Callbacks
Define functions for handling incoming messages, errors, connection open, and close events.

These functions can read from and write to `st.session_state`.

```python
def on_message(ws, message):
    # Parse and update Streamlit session state
    ...

def on_error(ws, error):
    # Handle error (log, update UI, etc.)
    ...

def on_close(ws, close_status_code, close_msg):
    # Update UI to show connection closed
    ...

def on_open(ws):
    # Send handshake or initial message
    ...
```

#### Step 2: Define the WebSocket URL Getter
This function should return the full WebSocket URL, using session state as needed:

```python
def get_ws_url():
    return f"wss://example.com/ws/{st.session_state.thread_id}"
```

#### Step 3: Specify State Requirements
List the session state keys that must exist and be "truthy" before starting the worker (e.g., `thread_id`, `username`):

```python
state_requirements = {"thread_id", "username"}
```

#### Step 4: Initialize All Needed Session State Variables
**Before** calling the worker, initialize any `st.session_state` variables that your callbacks or worker will use.

This avoids `KeyError`s and ensures a clean state.

```python
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "user_list" not in st.session_state:
    st.session_state.user_list = []

if "thread_id" not in st.session_state:
    st.session_state.thread_id = ""  # or a sensible default

if "username" not in st.session_state:
    st.session_state.username = ""   # or a sensible default
```

#### Step 5: Create the Config
Bundle your callbacks and requirements:

```python
cfg = get_config(
    on_message=on_message,
    on_error=on_error,
    on_close=on_close,
    on_open=on_open,
    get_ws_url=get_ws_url,
    state_requirements=state_requirements,
)
```

#### Step 6: Start the Worker
Call this **unconditionally** in your Streamlit script (ideally after all state initialization):

```python
start_ws_worker(cfg)
```

- The worker will only start when **all required state values are "truthy"** (not `None`, not empty string, etc.).
- If not ready, it will do nothing and check again on the next rerun.

### 3. Example: Real-Time Chat App

See [`./lg_st_ws/frontend/client.py`](./lg_st_ws/frontend/client.py) and [`./lg_st_ws/frontend/ws_impl.py`](./lg_st_ws/frontend/ws_impl.py) for a complete example of a real-time chat app using this pattern.

### 4. Best Practices and Tips
- **Always initialize** any session state variables used by your callbacks or the worker before starting it.
- **Update UI reactively** based on `st.session_state` changes made by your WebSocket callbacks.
- **Handle exceptions** in your callbacks to prevent silent failures.
- **Use `st.fragment`** for efficient, non-blocking UI updates, especially in long-running WebSocket connections.

### 5. Troubleshooting
- **WebSocket not connecting?**

  Ensure all `state_requirements` keys are set to valid, non-empty values before the worker is started.


- **UI not updating?**

  Make sure your callbacks update `st.session_state` and your UI reads from it.


- **Multiple threads?**

  The worker will only start one thread per session. If you need to reconnect, set `st.session_state.ws_thread = None` first.

### 6. Using the websocket to send data
Once your worker is running, you can send data to the server using the `ws_app` object stored in `st.session_state.ws_app`.

This object is an instance of [`websocket.WebSocketApp`](https://websocket-client.readthedocs.io/en/latest/app.html), and you can use its `.send()` method to transmit data (typically as JSON) to your WebSocket server.

#### How to Send Data
##### 1. Ensure the Worker is Running
- `st.session_state.ws_app` is only set **after** the worker thread has started and the connection has been established.
- If you try to send data before this, you may get an error (e.g., `AttributeError` or a broken pipe).
##### 2. Compose Your Message
- Typically, you’ll want to serialize your message as JSON.
- Include any relevant metadata (e.g., username, timestamp).
##### 3. Use `.send()` to Transmit
```python
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
```

**Reference**: See `send_user_input` in `./lg_st_ws/frontend/client.py` for a full example.

#### Best Practices and Tips
- **Check** that `ws_app` is not None before calling `.send()`.
- **Handle connection issues gracefully**: If the connection is not established, warn the user or queue the message for later.
- **Serialize your data**: Use `.json()` or similar methods to serialize your message objects.
- **Use metadata**: Include useful metadata (username, timestamp, etc.) for server-side handling.
- **Use common data models** between frontend and backend wherever possible.

### 7. Summary
This pattern gives you a safe, scalable way to integrate real-time WebSocket data into Streamlit, leveraging background threads and type-safe callback wiring.

**Initialize your state, set up your config, and let the worker manage connection lifecycle for you!**

Always double-check your integration and test for race conditions and UI consistency.
