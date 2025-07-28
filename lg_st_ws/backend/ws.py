import datetime

from langchain_core.runnables import RunnableConfig
from starlette.websockets import WebSocket

from lg_st_ws.backend.langgraph_orchestrator import LangGraphOrchestrator
from lg_st_ws.backend.thread_manager import ThreadManager
from lg_st_ws.common.models import (
    UserListMessage,
    MessageType,
    ChatMessage,
    GraphState,
)


class WebSocketSession:
    def __init__(
        self, thread_manager: ThreadManager, orchestrator: LangGraphOrchestrator
    ):
        self.thread_manager = thread_manager
        self.orchestrator = orchestrator

    async def shake_hands(self, ws: WebSocket, thread_id: str, username: str):
        await self.thread_manager.add_user(thread_id, username, ws)
        history_msg = await self.orchestrator.get_message_history(thread_id)
        await ws.send_json(history_msg.jsonable_dump())
        user_list_msg = UserListMessage(
            type=MessageType.user_list,
            thread_id=thread_id,
            users=self.thread_manager.get_usernames(thread_id),
            timestamp=datetime.datetime.now(datetime.UTC),
        )
        await ws.send_json(user_list_msg.jsonable_dump())

    async def ongoing_loop(
        self, ws: WebSocket, thread_id: str, graph_config: RunnableConfig
    ):
        while True:
            data = await ws.receive_json()
            if data.get("type") == MessageType.chat:
                chat_msg = ChatMessage(**data)
                lc_msg = chat_msg.to_lc_message()
                input_state = GraphState(messages=[lc_msg])
                await self.thread_manager.broadcast(thread_id, chat_msg)
                await self.orchestrator.broadcast_stream(
                    thread_id=thread_id,
                    input_state=input_state,
                    config=graph_config,
                    thread_manager=self.thread_manager,
                )
            else:
                continue
