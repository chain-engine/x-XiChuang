# -*- coding: utf-8 -*-
"""
对话服务模块

使用 LangGraph 编排对话流程：检索 -> 生成 -> 摘要。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.graph import END, StateGraph

from src.core.logger import logger
from src.schemas.chat import ChatGraphState, ChatServiceResult

if TYPE_CHECKING:
    from src.agent.media import MediaInput
    from src.agent.multimodal import MultimodalModelClient
    from src.agent.memory import ConversationMemory


class ChatService:
    """
    对话服务类

    编排完整的对话流程，包括知识库检索、模型生成、摘要更新。
    """

    def __init__(self) -> None:
        """初始化对话服务"""
        self._model_client: Optional["MultimodalModelClient"] = None
        self._memory: Optional["ConversationMemory"] = None
        self._graph = self._build_graph()

    @property
    def model_client(self) -> "MultimodalModelClient":
        """获取模型客户端（懒加载）"""
        if self._model_client is None:
            from src.agent.multimodal import MultimodalModelClient
            self._model_client = MultimodalModelClient()
        return self._model_client

    @property
    def memory(self) -> "ConversationMemory":
        """获取记忆管理（懒加载）"""
        if self._memory is None:
            from src.agent.memory import ConversationMemory
            self._memory = ConversationMemory()
        return self._memory

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

            logger.debug(f"Graph.retrieve_node: query={state.query[:50]}...")
            try:
                from src.agent.knowledge import knowledge_base
                snippets = await knowledge_base.aretrieve(state.query, k=4)
                if snippets:
                    joined = "\n\n---\n\n".join(snippets)
                    state.query = f"{state.query}\n\n[知识库检索结果]\n{joined}"
            except Exception as e:
                logger.warning(f"Knowledge retrieval failed: {e}")

            return state

        async def chat_node(state: ChatGraphState) -> ChatGraphState:
            """对话生成节点"""
            logger.debug(
                f"Graph.chat_node: messages={len(state.messages)}, "
                f"media={len(state.media_inputs)}, direct={state.use_direct_multimodal}"
            )

            try:
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
            except Exception as e:
                logger.error(f"Chat generation failed: {e}")
                state.answer = f"抱歉，生成回答时发生错误：{str(e)}"
                state.messages.append(AIMessage(content=state.answer))

            return state

        async def summarize_node(state: ChatGraphState) -> ChatGraphState:
            """摘要节点"""
            try:
                trimmed = self.memory.trim_messages(state.messages)
                summary = await self.memory.update_summary(
                    session_id="",
                    messages=trimmed,
                    provider=state.provider,
                )
                self.memory.save_messages("", trimmed)
                state.summary = summary
                state.messages = trimmed
            except Exception as e:
                logger.warning(f"Summary generation failed: {e}")
                state.summary = None

            return state

        # 注册节点
        graph.add_node("retrieve", retrieve_node)
        graph.add_node("chat", chat_node)
        graph.add_node("summarize", summarize_node)

        # 设置流程
        graph.set_entry_point("retrieve")
        graph.add_edge("retrieve", "chat")
        graph.add_edge("chat", "summarize")
        graph.add_edge("summarize", END)

        return graph.compile()

    async def handle_chat(
        self,
        session_id: str,
        query: str,
        history: List[BaseMessage],
        media_inputs: List["MediaInput"],
        use_direct_multimodal: bool = True,
        provider: Optional[str] = None,
    ) -> ChatServiceResult:
        """
        执行完整的对话流程

        Args:
            session_id: 会话 ID
            query: 用户问题
            history: 历史消息
            media_inputs: 多模态输入
            use_direct_multimodal: 是否直接走多模态模型
            provider: 模型提供商

        Returns:
            ChatServiceResult: 包含 answer、summary、trimmed_history
        """
        logger.info(
            f"Handling chat: session_id={session_id}, "
            f"query_len={len(query)}, media_count={len(media_inputs)}"
        )

        # 1. 获取历史消息
        history_messages = self.memory.get_messages(session_id)
        for msg in history:
            if hasattr(msg, "role"):
                role = getattr(msg, "role", "user")
                content = getattr(msg, "content", "")
                if role == "user":
                    history_messages.append(HumanMessage(content=content))
                else:
                    history_messages.append(AIMessage(content=content))

        # 2. 构建初始状态
        graph_state = ChatGraphState(
            messages=history_messages,
            media_inputs=media_inputs,
            query=query,
            use_direct_multimodal=use_direct_multimodal,
            provider=provider,
        )

        # 3. 执行图
        try:
            raw_final_state = await self._graph.ainvoke(graph_state)
            final_state = (
                ChatGraphState.model_validate(raw_final_state)
                if isinstance(raw_final_state, dict)
                else raw_final_state
            )
        except Exception as e:
            logger.error(f"Graph execution failed: {e}")
            return ChatServiceResult(
                answer=f"抱歉，处理您的请求时发生错误：{str(e)}",
                summary=None,
                trimmed_history=history_messages,
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

    async def handle_stream(
        self,
        session_id: str,
        query: str,
        history: List[BaseMessage],
        media_inputs: List["MediaInput"],
        use_direct_multimodal: bool = True,
        provider: Optional[str] = None,
    ):
        """
        流式对话处理

        Args:
            session_id: 会话 ID
            query: 用户问题
            history: 历史消息
            media_inputs: 多模态输入
            use_direct_multimodal: 是否直接走多模态模型
            provider: 模型提供商

        Yields:
            str: 生成的文本片段
        """
        # 知识库检索
        try:
            from src.agent.knowledge import knowledge_base
            if query.strip():
                snippets = await knowledge_base.aretrieve(query, k=4)
                if snippets:
                    joined = "\n\n---\n\n".join(snippets)
                    query = f"{query}\n\n[知识库检索结果]\n{joined}"
        except Exception as e:
            logger.warning(f"Knowledge retrieval failed: {e}")

        # 流式生成
        async for chunk in self.model_client.stream_chat(
            session_id=session_id,
            query=query,
            history=history,
            media_inputs=media_inputs,
            use_direct_multimodal=use_direct_multimodal,
            provider=provider,
        ):
            yield chunk


# 全局服务实例
_chat_service: Optional[ChatService] = None


def get_chat_service() -> ChatService:
    """获取全局对话服务实例"""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
