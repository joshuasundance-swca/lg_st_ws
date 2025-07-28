import datetime

from fastapi import WebSocket

from lg_st_ws.common.models import (
    SystemEventMessage,
    MessageType,
    SystemEvent,
    JSONModel,
)


class ThreadManager:
    def __init__(self):
        self.thread_users: dict[str, dict[str, WebSocket]] = {}

    def get_usernames(self, thread_id: str) -> list[str]:
        return list(self.thread_users.get(thread_id, {}).keys())

    def get_connections(self, thread_id: str) -> list[WebSocket]:
        return list(self.thread_users.get(thread_id, {}).values())

    async def add_user(self, thread_id: str, username: str, websocket: WebSocket):
        if thread_id not in self.thread_users:
            self.thread_users[thread_id] = {}
        self.thread_users[thread_id][username] = websocket
        join_msg = SystemEventMessage(
            type=MessageType.system_event,
            event=SystemEvent.user_joined,
            thread_id=thread_id,
            username=username,
            content=f"{username} has connected to thread {thread_id}.",
            timestamp=datetime.datetime.now(datetime.UTC),
        )
        await self.broadcast(thread_id, join_msg)

    async def remove_user(self, thread_id: str, username: str):
        if thread_id in self.thread_users and username in self.thread_users[thread_id]:
            del self.thread_users[thread_id][username]
            if not self.thread_users[thread_id]:
                del self.thread_users[thread_id]
        leave_msg = SystemEventMessage(
            type=MessageType.system_event,
            event=SystemEvent.user_left,
            thread_id=thread_id,
            username=username,
            content=f"{username} has disconnected from thread {thread_id}.",
            timestamp=datetime.datetime.now(datetime.UTC),
        )
        await self.broadcast(thread_id, leave_msg)

    async def broadcast(self, thread_id: str, msg: JSONModel):
        for ws in self.get_connections(thread_id):
            await ws.send_json(msg.jsonable_dump())
