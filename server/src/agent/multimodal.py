# -*- coding: utf-8 -*-
"""
多模态处理模块

支持文本、语音、图片、视频的多模态对话处理。
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import os
import warnings
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING, AsyncGenerator, Iterable, List, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from openai import OpenAI
from pydantic import BaseModel

# 在导入 pydub 前尽量设置 FFMPEG_BINARY，避免 pydub 在 import 阶段发出 RuntimeWarning。
_resolved_ffmpeg_binary = os.getenv("FFMPEG_BINARY", "").strip()
if not _resolved_ffmpeg_binary:
    try:
        import imageio_ffmpeg

        _resolved_ffmpeg_binary = imageio_ffmpeg.get_ffmpeg_exe()
        os.environ["FFMPEG_BINARY"] = _resolved_ffmpeg_binary
    except Exception:  # noqa: BLE001
        _resolved_ffmpeg_binary = ""

# pydub 在 Windows 下会通过 which("ffmpeg") 查找固定文件名 ffmpeg.exe。
# imageio-ffmpeg 提供的是版本化文件名，功能可用但会产生一条误导性告警，这里定向抑制。
warnings.filterwarnings(
    "ignore",
    message="Couldn't find ffmpeg or avconv - defaulting to ffmpeg, but may not work",
    category=RuntimeWarning,
    module="pydub.utils",
)

from pydub import AudioSegment

from src.config.settings import Settings, settings
from src.core.logger import logger

if TYPE_CHECKING:
    from src.agent.model import ModelProvider


def _configure_ffmpeg_binary() -> None:
    """
    为 pydub 配置 ffmpeg 可执行文件路径。

    优先级：
    1. 环境变量 FFMPEG_BINARY（用户显式配置）
    2. imageio-ffmpeg 自带可执行文件
    3. 系统 PATH（保持 pydub 默认行为）
    """
    ffmpeg_binary = os.getenv("FFMPEG_BINARY", "").strip()
    if ffmpeg_binary:
        AudioSegment.converter = ffmpeg_binary
        logger.info("Using ffmpeg from FFMPEG_BINARY: {}", ffmpeg_binary)
        return

    try:
        if _resolved_ffmpeg_binary:
            AudioSegment.converter = _resolved_ffmpeg_binary
            logger.info("Using ffmpeg from imageio-ffmpeg: {}", _resolved_ffmpeg_binary)
            return
        import imageio_ffmpeg

        ffmpeg_binary = imageio_ffmpeg.get_ffmpeg_exe()
        AudioSegment.converter = ffmpeg_binary
        logger.info("Using ffmpeg from imageio-ffmpeg: {}", ffmpeg_binary)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "ffmpeg binary not explicitly configured; pydub will fallback to system PATH. detail={}",
            exc,
        )


_configure_ffmpeg_binary()


class MediaType:
    """媒体类型常量"""

    TEXT = "text"
    VOICE = "voice"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    AUTO = "auto"


class MediaInput(BaseModel):
    """
    统一的媒体输入模型

    支持两种传入方式：
    1. URL：通过可访问的 HTTP(S) 地址引用媒体资源
    2. 字节内容：通过上传文件获得的原始 bytes
    """

    type: str = MediaType.AUTO
    url: Optional[str] = None
    filename: Optional[str] = None
    bytes_base64: Optional[bytes] = None


class MultimodalChatResult(BaseModel):
    """多模态对话的结果结构"""

    answer: str
    messages: List[BaseMessage]


class MultimodalModelClient:
    """
    多模态模型客户端封装

    支持两种语音路径：
    1）语音 -> Whisper 语音转文字 -> 文本大模型
    2）语音/图片/视频 -> 直接送入多模态大模型
    """

    def __init__(self, settings_obj: Settings = None) -> None:
        self.settings = settings_obj or settings
        # 用于语音转写的 OpenAI Whisper 客户端（可选）
        openai_api_key = os.getenv("OPENAI_API_KEY") or self.settings.OPENAI_API_KEY or ""
        self._audio_client: Optional[OpenAI] = (
            OpenAI(api_key=openai_api_key) if openai_api_key else None
        )

    async def chat(
        self,
        session_id: str,
        query: str,
        history: Iterable[BaseMessage],
        media_inputs: List[MediaInput],
        use_direct_multimodal: bool,
        provider: str | None,
    ) -> str:
        """
        统一的聊天入口

        Args:
            session_id: 会话ID
            query: 用户文本输入
            history: 历史消息
            media_inputs: 多模态输入列表
            use_direct_multimodal: 是否直接走多模态模型
            provider: 指定模型提供方

        Returns:
            模型回答文本
        """
        # 延迟导入避免循环依赖
        from src.agent.model import ModelProvider, build_chat_model

        logger.debug(
            "Multimodal chat: session_id=%s, media_count=%d, direct=%s, provider=%s",
            session_id,
            len(media_inputs),
            use_direct_multimodal,
            provider,
        )

        def _is_invalid_api_key_error(exc: Exception) -> bool:
            # 兼容不同 SDK 的报错格式；这里主要匹配 DashScope 的 invalid_api_key
            msg = str(exc).lower()
            return ("invalid_api_key" in msg) or ("incorrect api key" in msg)

        # 候选策略：
        # - 显式指定 provider：严格仅使用该 provider（避免 UI 选了 GLM 却静默回退到千问）
        # - 未指定 provider：按默认优先级自动选择
        default_priority = [
            ModelProvider.tongyi.value,
            ModelProvider.deepseek.value,
            ModelProvider.glm.value,
            ModelProvider.doubao.value,
            ModelProvider.kimi.value,
        ]
        if provider:
            normalized = provider.strip().lower()
            if normalized not in {p.value for p in ModelProvider if p != ModelProvider.mock}:
                raise ValueError(f"Unsupported provider: {provider}")
            if not self.settings.validate_model_config(normalized):
                raise ValueError(
                    f"Provider '{normalized}' is not configured. Please check API key/base/model settings."
                )
            candidates = [normalized]
        else:
            # 自动模式仅使用已配置 provider
            candidates = [c for c in default_priority if self.settings.validate_model_config(c)]

        async def _ainvoke_with_provider_fallback(messages_to_send: List[BaseMessage]) -> str:
            last_exc: Exception | None = None
            for cand in candidates:
                llm, used_provider = build_chat_model(self.settings, preferred=cand)
                try:
                    response: AIMessage = await llm.ainvoke(messages_to_send)
                    logger.debug(
                        "Multimodal chat succeeded with provider=%s",
                        used_provider.value,
                    )
                    return str(response.content)
                except Exception as exc:  # noqa: BLE001
                    if _is_invalid_api_key_error(exc):
                        last_exc = exc
                        logger.warning(
                            "Provider auth failed (invalid_api_key). provider=%s, try next. error=%s",
                            cand,
                            exc,
                        )
                        continue
                    raise

            # 自动模式下 candidates 可能为空：交给 build_chat_model 兜底（mock 或默认策略）
            if not candidates:
                llm, used_provider = build_chat_model(self.settings, preferred=provider)
                response: AIMessage = await llm.ainvoke(messages_to_send)
                logger.debug(
                    "Multimodal chat succeeded with provider=%s (fallback)",
                    used_provider.value,
                )
                return str(response.content)

            assert last_exc is not None
            raise last_exc

        messages: List[BaseMessage] = list(history)

        # 路径一：语音 -> Whisper -> 文本大模型
        if not use_direct_multimodal and media_inputs:
            transcript = await self._transcribe_first_audio(media_inputs)
            if transcript:
                merged_query = (
                    f"{query}\n\n[语音转写]\n{transcript}" if query else transcript
                )
                messages.append(HumanMessage(content=merged_query))
                answer = await _ainvoke_with_provider_fallback(messages)
                logger.debug("Text-only response length after STT: {}", len(answer or ""))
                return answer

        # 路径二：直接多模态（音频/图片/视频）
        content_parts: list[dict] = []

        if query:
            content_parts.append({"type": "text", "text": query})

        for media in media_inputs:
            media_type = self._detect_media_type(media)
            if not media_type:
                continue

            source: str | None = None
            if media.url:
                source = media.url
            elif media.bytes_base64 is not None:
                encoded = base64.b64encode(media.bytes_base64).decode("utf-8")
                mime = self._guess_mime(media_type, media.filename)
                source = f"data:{mime};base64,{encoded}"

            if not source:
                continue

            if media_type == MediaType.IMAGE:
                content_parts.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": source},
                    }
                )
            elif media_type in (MediaType.AUDIO, MediaType.VOICE):
                content_parts.append(
                    {
                        "type": "input_audio",
                        "input_audio": {"data": source},
                    }
                )
            elif media_type == MediaType.VIDEO:
                content_parts.append(
                    {
                        "type": "video_url",
                        "video_url": {"url": source},
                    }
                )

        messages.append(HumanMessage(content=content_parts or query))
        answer = await _ainvoke_with_provider_fallback(messages)
        logger.debug("Multimodal response length: {}", len(answer or ""))
        return answer

    async def stream_chat(
        self,
        session_id: str,
        query: str,
        history: Iterable[BaseMessage],
        media_inputs: List[MediaInput],
        use_direct_multimodal: bool,
        provider: str | None,
    ) -> AsyncGenerator[str, None]:
        """
        流式聊天入口，逐步生成回答

        Yields:
            每个 token/chunk 的文本片段
        """
        from src.agent.model import ModelProvider, build_chat_model

        def _is_invalid_api_key_error(exc: Exception) -> bool:
            msg = str(exc).lower()
            return ("invalid_api_key" in msg) or ("incorrect api key" in msg)

        default_priority = [
            ModelProvider.tongyi.value,
            ModelProvider.deepseek.value,
            ModelProvider.glm.value,
            ModelProvider.doubao.value,
            ModelProvider.kimi.value,
        ]
        if provider:
            normalized = provider.strip().lower()
            if normalized not in {p.value for p in ModelProvider if p != ModelProvider.mock}:
                raise ValueError(f"Unsupported provider: {provider}")
            if not self.settings.validate_model_config(normalized):
                raise ValueError(
                    f"Provider '{normalized}' is not configured. Please check API key/base/model settings."
                )
            candidates = [normalized]
        else:
            candidates = [c for c in default_priority if self.settings.validate_model_config(c)]

        messages: List[BaseMessage] = list(history)

        # 处理语音输入（非流式）
        if not use_direct_multimodal and media_inputs:
            transcript = await self._transcribe_first_audio(media_inputs)
            if transcript:
                merged_query = f"{query}\n\n[语音转写]\n{transcript}" if query else transcript
                messages.append(HumanMessage(content=merged_query))
                # 流式输出
                async for chunk in self._stream_invoke(messages, candidates, provider):
                    yield chunk
                return

        # 构建多模态消息
        content_parts: list[dict] = []
        if query:
            content_parts.append({"type": "text", "text": query})

        for media in media_inputs:
            media_type = self._detect_media_type(media)
            if not media_type:
                continue
            source: str | None = None
            if media.url:
                source = media.url
            elif media.bytes_base64 is not None:
                encoded = base64.b64encode(media.bytes_base64).decode("utf-8")
                mime = self._guess_mime(media_type, media.filename)
                source = f"data:{mime};base64,{encoded}"
            if not source:
                continue
            if media_type == MediaType.IMAGE:
                content_parts.append({"type": "image_url", "image_url": {"url": source}})
            elif media_type in (MediaType.AUDIO, MediaType.VOICE):
                content_parts.append({"type": "input_audio", "input_audio": {"data": source}})
            elif media_type == MediaType.VIDEO:
                content_parts.append({"type": "video_url", "video_url": {"url": source}})

        messages.append(HumanMessage(content=content_parts or query))

        # 流式输出
        async for chunk in self._stream_invoke(messages, candidates, provider):
            yield chunk

    async def _stream_invoke(
        self,
        messages: List[BaseMessage],
        candidates: List[str],
        provider: str | None,
    ) -> AsyncGenerator[str, None]:
        """流式调用模型，带回退"""
        from src.agent.model import ModelProvider, build_chat_model

        last_exc: Exception | None = None
        for cand in candidates:
            llm, used_provider = build_chat_model(self.settings, preferred=cand)
            try:
                async for chunk in llm.astream(messages):
                    if chunk.content:
                        yield str(chunk.content)
                logger.debug("Stream chat succeeded with provider=%s", used_provider.value)
                return
            except Exception as exc:
                msg = str(exc).lower()
                if "invalid_api_key" in msg or "incorrect api key" in msg:
                    last_exc = exc
                    logger.warning("Provider auth failed, trying next: %s", exc)
                    continue
                raise

        # 兜底
        if not candidates:
            llm, used_provider = build_chat_model(self.settings, preferred=provider)
            async for chunk in llm.astream(messages):
                if chunk.content:
                    yield str(chunk.content)
            return

        if last_exc:
            raise last_exc

    async def _transcribe_first_audio(
        self, media_inputs: List[MediaInput]
    ) -> str | None:
        """
        从媒体列表中取第一段音频，调用 Whisper 做语音转文字

        Args:
            media_inputs: 媒体列表

        Returns:
            转写文本；若无可用音频、未配置 Whisper、或转写失败则返回 None
        """
        if not self._audio_client:
            logger.debug("OPENAI_API_KEY not set, skip STT path.")
            return None

        audio_bytes: bytes | None = None
        for media in media_inputs:
            media_type = self._detect_media_type(media)
            if media_type in (MediaType.AUDIO, MediaType.VOICE) and media.bytes_base64:
                audio_bytes = media.bytes_base64
                break

        if not audio_bytes:
            return None

        try:
            return await asyncio.to_thread(
                self._transcribe_bytes_sync, audio_bytes
            )
        except Exception as exc:
            logger.warning("Audio transcription failed: {}", exc)
            return None

    def _transcribe_bytes_sync(self, data: bytes) -> str | None:
        """同步执行的语音转写逻辑"""
        audio_segment = AudioSegment.from_file(io.BytesIO(data))
        with NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            audio_segment.export(tmp_path, format="mp3")
            with open(tmp_path, "rb") as f:
                result = self._audio_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    response_format="json",
                )
            return getattr(result, "text", None)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _detect_media_type(self, media: MediaInput) -> str | None:
        """
        检测媒体类型

        Args:
            media: 媒体输入对象

        Returns:
            媒体类型字符串
        """
        if media.type != MediaType.AUTO:
            return media.type

        if media.filename:
            name = media.filename.lower()
            if any(name.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]):
                return MediaType.IMAGE
            if any(name.endswith(ext) for ext in [".mp3", ".wav", ".m4a", ".aac", ".webm", ".ogg"]):
                return MediaType.AUDIO
            if any(name.endswith(ext) for ext in [".mp4", ".mov", ".avi", ".mkv", ".webm"]):
                return MediaType.VIDEO

        return None

    @staticmethod
    def _guess_mime(media_type: str, filename: str | None) -> str:
        """根据媒体类型和文件名猜测 MIME 类型"""
        if media_type == MediaType.IMAGE:
            if filename:
                ext = filename.lower().split(".")[-1]
                mime_map = {
                    "png": "image/png",
                    "jpg": "image/jpeg",
                    "jpeg": "image/jpeg",
                    "gif": "image/gif",
                    "webp": "image/webp",
                }
                return mime_map.get(ext, "image/png")
            return "image/png"
        if media_type in (MediaType.AUDIO, MediaType.VOICE):
            if filename:
                ext = filename.lower().split(".")[-1]
                mime_map = {
                    "mp3": "audio/mpeg",
                    "wav": "audio/wav",
                    "m4a": "audio/mp4",
                    "aac": "audio/aac",
                    "ogg": "audio/ogg",
                    "webm": "audio/webm",
                }
                return mime_map.get(ext, "audio/mpeg")
            return "audio/mpeg"
        if media_type == MediaType.VIDEO:
            if filename:
                ext = filename.lower().split(".")[-1]
                mime_map = {
                    "mp4": "video/mp4",
                    "mov": "video/quicktime",
                    "avi": "video/x-msvideo",
                    "mkv": "video/x-matroska",
                    "webm": "video/webm",
                }
                return mime_map.get(ext, "video/mp4")
            return "video/mp4"
        return "application/octet-stream"
