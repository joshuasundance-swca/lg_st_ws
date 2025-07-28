from fastapi import FastAPI, WebSocket
from starlette.websockets import WebSocketDisconnect

from lg_st_ws.backend.langgraph_orchestrator import LangGraphOrchestrator
from lg_st_ws.backend.thread_manager import ThreadManager
from lg_st_ws.backend.ws import WebSocketSession
from lg_st_ws.common.config import (
    BOT_NAME,
    CUSTOM_INSTRUCTIONS,
    MODEL_NAME,
)
from lg_st_ws.common.models import (
    HandshakeMessage,
)

app = FastAPI()
thread_manager = ThreadManager()
orchestrator = LangGraphOrchestrator(
    bot_name=BOT_NAME,
    custom_instructions=CUSTOM_INSTRUCTIONS,
    model_name=MODEL_NAME,
)
ws_session = WebSocketSession(thread_manager, orchestrator)


@app.websocket("/thread/{thread_id}/ws")
async def websocket_endpoint(ws: WebSocket, thread_id: str):
    await ws.accept()
    graph_config = orchestrator.get_graph_config(thread_id)
    handshake_data = await ws.receive_json()
    try:
        handshake = HandshakeMessage(**handshake_data)
    except Exception:
        await ws.close(code=4000)
        return
    username = handshake.username
    await ws_session.shake_hands(ws, thread_id, username)
    try:
        await ws_session.ongoing_loop(ws, thread_id, graph_config)
    except WebSocketDisconnect:
        await ws_session.thread_manager.remove_user(thread_id, username)
