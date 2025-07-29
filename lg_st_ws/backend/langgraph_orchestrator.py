import datetime
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.constants import START, END
from langgraph.graph import StateGraph

from lg_st_ws.backend.thread_manager import ThreadManager
from lg_st_ws.common.models import (
    GraphState,
    MessageHistory,
    ChatMessage,
)
from lg_st_ws.common.util import serialize_history


class LangGraphOrchestrator:
    def __init__(
        self,
        bot_name: str,
        custom_instructions: str,
        model_name: str,
        checkpointer: BaseCheckpointSaver | None = None,
    ):
        self.llm = ChatOpenAI(model=model_name)
        self.bot_name = bot_name
        self.custom_instructions = custom_instructions
        self.checkpointer = checkpointer or InMemorySaver()
        self.graph = self._build_graph()

    def _build_graph(self):
        async def should_respond(
            state: GraphState, config: RunnableConfig
        ) -> Literal["yes", "no"]:
            most_recent_message: HumanMessage = state["messages"][-1]
            bot_name: str = config["configurable"]["bot_name"]
            human_addressing_bot: bool = "@" + bot_name in str(
                most_recent_message.content
            )
            return "yes" if human_addressing_bot else "no"

        async def respond(state: GraphState, config: RunnableConfig) -> GraphState:
            bot_name = config["configurable"]["bot_name"]
            custom_instructions = config["configurable"].get("custom_instructions", "")

            _sysmsg = (
                "You are participating in a multi-user conversation. "
                "Feel free to respond to any message from any user since the last time you spoke. "
                f"Your username ({bot_name}) and timestamp will be appended automatically by the server. "
                "DO NOT include them at the beginning of your response. "
                "Use the @ symbol to tag users in the conversation. "
                f"{custom_instructions}"
            ).strip()

            sysmsg = SystemMessage(content=_sysmsg)

            def inject_username(msg: BaseMessage) -> BaseMessage:
                if isinstance(msg, HumanMessage):
                    username = msg.metadata["username"]
                    time_str = msg.metadata["timestamp"]
                    content = msg.content
                    new_content = f"**{username}** [{time_str}]: {content}"
                    msg = HumanMessage(content=new_content)
                elif isinstance(msg, AIMessage):
                    username = msg.response_metadata["username"]
                    timestamp = msg.response_metadata["timestamp"]
                    content = msg.content
                    new_content = f"**{username}** [{timestamp}]: {content}"
                    msg = AIMessage(content=new_content)
                return msg

            msgs = [inject_username(msg) for msg in state["messages"]]
            response: BaseMessage = await self.llm.ainvoke([sysmsg] + msgs)
            response.response_metadata["username"] = self.bot_name
            response.response_metadata["timestamp"] = datetime.datetime.now(
                datetime.UTC
            ).isoformat()
            return {"messages": [response]}

        graph_builder = StateGraph(state_schema=GraphState)  # type: ignore
        graph_builder.add_node("respond", respond)  # type: ignore
        graph_builder.add_conditional_edges(
            START,
            should_respond,
            {"yes": "respond", "no": END},
        )
        return graph_builder.compile(checkpointer=self.checkpointer)

    def get_graph_config(self, thread_id: str) -> RunnableConfig:
        return RunnableConfig(
            configurable={
                "thread_id": thread_id,
                "bot_name": self.bot_name,
                "custom_instructions": self.custom_instructions,
            }
        )

    async def get_message_history(self, thread_id: str) -> MessageHistory:
        graph_config = self.get_graph_config(thread_id)
        state_snapshot = await self.graph.aget_state(graph_config)
        state_values = state_snapshot.values
        raw_history = state_values.get("messages", [])
        history_msg = MessageHistory(
            thread_id=thread_id,
            messages=serialize_history(raw_history),
            timestamp=datetime.datetime.now(datetime.UTC),
        )
        return history_msg

    async def broadcast_stream(
        self,
        thread_id: str,
        input_state: GraphState,
        config: RunnableConfig,
        thread_manager: ThreadManager,
    ):
        async for update in self.graph.astream(
            input_state,
            config,
            stream_mode="updates",
        ):
            ai_msg = update["respond"]["messages"][0]
            if not hasattr(ai_msg, "metadata") or not ai_msg.metadata:
                ai_msg.metadata = {}
            ai_msg.metadata["username"] = self.bot_name
            ai_msg.metadata["timestamp"] = datetime.datetime.now(
                datetime.UTC
            ).isoformat()
            chat_msg = ChatMessage.from_lc_message(thread_id, ai_msg)
            await thread_manager.broadcast(thread_id, chat_msg)
