# -*- coding: utf-8 -*-
"""
对话服务模块

使用 LangGraph 编排对话流程：检索 -> 生成 -> 摘要。
所有节点都使用真实的 session_id 进行记忆路由，避免「所有用户共享一份会话」。
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


# 仅当「本会话历史长度超过该阈值」才生成摘要，避免每轮都打 LLM
SUMMARY_TRIGGER_MIN_MESSAGES = 6


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
        1. retrieve: 知识库检索，把片段拼成一个独立的「参考资料」HumanMessage
        2. chat: 调用模型生成回答
        3. summarize: 当消息量超过阈值时调用 LLM 摘要
        """

        graph = StateGraph(ChatGraphState)

        async def retrieve_node(state: ChatGraphState) -> ChatGraphState:
            """知识库检索节点：把检索片段作为独立 HumanMessage 注入上下文"""
            if not state.query.strip():
                return state

            sid = state.session_id
            logger.debug("Graph.retrieve_node: sid=%s, query=%s...", sid, state.query[:50])
            try:
                from src.agent.knowledge import knowledge_base
                snippets = await knowledge_base.aretrieve(state.query, k=4)
                if snippets:
                    joined = "\n\n---\n\n".join(snippets)
                    context_msg = HumanMessage(
                        content=(
                            "以下是参考资料（如与用户问题相关请参考作答，否则忽略）：\n\n"
                            f"{joined}"
                        )
                    )
                    # 紧跟在用户原始问题之后插入上下文消息
                    state.messages.append(context_msg)
            except Exception as e:
                logger.warning(f"Knowledge retrieval failed: {e}")

            return state

        async def chat_node(state: ChatGraphState) -> ChatGraphState:
            """对话生成节点"""
            logger.debug(
                "Graph.chat_node: sid=%s, messages=%d, media=%d, direct=%s",
                state.session_id, len(state.messages),
                len(state.media_inputs), state.use_direct_multimodal,
            )

            try:
                answer_text = await self.model_client.chat(
                    session_id=state.session_id,
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
            """摘要节点：仅当消息量超过阈值才调用 LLM，避免每轮额外 token 消耗"""
            try:
                sid = state.session_id
                trimmed = self.memory.trim_messages(state.messages)

                # 仅当本会话有足够历史才生成摘要
                if len(trimmed) >= SUMMARY_TRIGGER_MIN_MESSAGES and sid:
                    summary = await self.memory.update_summary(
                        session_id=sid,
                        messages=trimmed,
                        provider=state.provider,
                    )
                    state.summary = summary
                else:
                    state.summary = self.memory.get_summary(sid) if sid else None

                # 同步到 in-memory（进程内 LRU 缓存）
                if sid:
                    self.memory.save_messages(sid, trimmed)
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
            session_id: 会话 ID（必传，将用于记忆路由）
            query: 用户问题
            history: 历史消息（通常由调用方从持久层传入；这里会再叠加上 in-memory 缓存）
            media_inputs: 多模态输入
            use_direct_multimodal: 是否直接走多模态模型
            provider: 模型提供商

        Returns:
            ChatServiceResult: 包含 answer、summary、trimmed_history
        """
        logger.info(
            "Handling chat: session_id=%s, query_len=%d, media_count=%d",
            session_id, len(query), len(media_inputs),
        )

        # 1. 合并：in-memory 历史 + 调用方传入的 history
        history_messages: List[BaseMessage] = []
        if session_id:
            history_messages.extend(self.memory.get_messages(session_id))
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
            session_id=session_id or "",
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

        检索片段作为独立的 HumanMessage 注入上下文，避免污染用户原始 query。

        Yields:
            str: 生成的文本片段
        """
        sid = session_id or ""

        # 知识库检索（作为独立上下文消息，不污染 user query）
        knowledge_msg: Optional[HumanMessage] = None
        if query.strip():
            try:
                from src.agent.knowledge import knowledge_base
                snippets = await knowledge_base.aretrieve(query, k=4)
                if snippets:
                    joined = "\n\n---\n\n".join(snippets)
                    knowledge_msg = HumanMessage(
                        content=(
                            "以下是参考资料（如与用户问题相关请参考作答，否则忽略）：\n\n"
                            f"{joined}"
                        )
                    )
            except Exception as e:
                logger.warning(f"Knowledge retrieval failed: {e}")

        # 拼接历史：in-memory + 调用方传入 + 检索上下文
        merged_history: List[BaseMessage] = []
        if sid:
            merged_history.extend(self.memory.get_messages(sid))
        for msg in history:
            if hasattr(msg, "role"):
                role = getattr(msg, "role", "user")
                content = getattr(msg, "content", "")
                if role == "user":
                    merged_history.append(HumanMessage(content=content))
                else:
                    merged_history.append(AIMessage(content=content))
        if knowledge_msg is not None:
            merged_history.append(knowledge_msg)

        # 流式生成
        async for chunk in self.model_client.stream_chat(
            session_id=sid,
            query=query,
            history=merged_history,
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