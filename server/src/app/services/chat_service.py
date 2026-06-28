# -*- coding: utf-8 -*-
"""
对话服务模块

使用 LangGraph 编排对话流程：检索 -> 生成 -> 摘要。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from src.config.settings import settings
from src.core.logger import logger
from src.agent.media import MediaInput
from src.agent.multimodal import MultimodalModelClient
from src.agent.memory import ConversationMemory
from src.agent.knowledge import knowledge_base


class ChatGraphState(BaseModel):
    """
    LangGraph 对话状态

    Attributes:
        messages: 当前所有对话消息
        media_inputs: 本次请求的多模态输入
        query: 用户文本问题
        use_direct_multimodal: 是否直接走多模态模型
        provider: 模型提供方
        answer: 模型回答
        summary: 对话摘要
    """

    messages: List[BaseMessage] = Field(default_factory=list)
    media_inputs: List[MediaInput] = Field(default_factory=list)
    query: str = ""
    use_direct_multimodal: bool = True
    provider: Optional[str] = None
    answer: Optional[str] = None
    summary: Optional[str] = None


@dataclass
class ChatServiceResult:
    """对话服务结果"""

    answer: str
    summary: str | None
    trimmed_history: List[HumanMessage | AIMessage]


class ChatService:
    """对话服务类，编排完整的对话流程"""

    def __init__(self) -> None:
        self.model_client = MultimodalModelClient()
        self.memory = ConversationMemory()
        self._graph = self._build_graph()

    def _build_graph(self):
        """
        构建 LangGraph 对话流程

        流程：
        1. retrieve: 知识库检索，将片段拼接到 query
        2. chat: 调用模型生成回答
        3. summarize: 修剪上下文并生成摘要

        Returns:
            编译后的 LangGraph 图
        """

        graph = StateGraph(ChatGraphState)

        async def retrieve_node(state: ChatGraphState) -> ChatGraphState:
            """知识库检索节点"""
            if not state.query.strip():
                return state

            logger.debug("Graph.retrieve_node: query=%s", state.query)
            snippets = await knowledge_base.aretrieve(state.query, k=4)
            if not snippets:
                return state

            joined = "\n\n---\n\n".join(snippets)
            state.query = f"{state.query}\n\n[知识库检索结果]\n{joined}"
            return state

        async def chat_node(state: ChatGraphState) -> ChatGraphState:
            """对话生成节点"""
            logger.debug(
                "Graph.chat_node: messages=%d, media=%d, direct=%s",
                len(state.messages),
                len(state.media_inputs),
                state.use_direct_multimodal,
            )

            answer_text = await self.model_client.chat(
                session_id="",
                query=state.query,
                history=state.messages,
                media_inputs=state.media_inputs,
                use_direct_multimodal=state.use_direct_multimodal,
                provider=state.provider,
            )

            state.answer = answer_text
            state.messages.append(AIMessage(content=answer_text))
            return state

        async def summarize_node(state: ChatGraphState) -> ChatGraphState:
            """摘要节点"""
            trimmed = self.memory.trim_messages(state.messages)
            summary = await self.memory.update_summary(
                session_id="",
                messages=trimmed,
                provider=state.provider,
            )
            self.memory.save_messages("", trimmed)
            state.summary = summary
            state.messages = trimmed
            return state

        graph.add_node("retrieve", retrieve_node)
        graph.add_node("chat", chat_node)
        graph.add_node("summarize", summarize_node)
        graph.set_entry_point("retrieve")
        graph.add_edge("retrieve", "chat")
        graph.add_edge("chat", "summarize")
        graph.add_edge("summarize", END)

        return graph.compile()

    async def handle_chat(self, request) -> ChatServiceResult:
        """
        执行完整的对话流程

        Args:
            request: 对话请求对象，包含 session_id、query、history 等字段

        Returns:
            ChatServiceResult: 包含 answer、summary、trimmed_history
        """
        # 1. 合并历史消息
        history_messages = self.memory.get_messages(request.session_id)

        for msg in request.history:
            if msg.role == "user":
                history_messages.append(HumanMessage(content=msg.content))
            else:
                history_messages.append(AIMessage(content=msg.content))

        # 2. 构建初始状态
        media_inputs: List[MediaInput] = request.media_inputs or []
        logger.info("Handling chat with %d media inputs", len(media_inputs))

        graph_state = ChatGraphState(
            messages=history_messages,
            media_inputs=media_inputs,
            query=request.query,
            use_direct_multimodal=request.use_direct_multimodal,
            provider=getattr(request, "provider", None),
        )

        # 3. 执行图
        raw_final_state = await self._graph.ainvoke(graph_state)
        final_state = (
            ChatGraphState.model_validate(raw_final_state)
            if isinstance(raw_final_state, dict)
            else raw_final_state
        )

        # 4. 提取结果
        trimmed = [
            m for m in final_state.messages
            if isinstance(m, (HumanMessage, AIMessage))
        ]

        return ChatServiceResult(
            answer=final_state.answer or "",
            summary=final_state.summary,
            trimmed_history=trimmed,
        )
