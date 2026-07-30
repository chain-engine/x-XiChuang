# -*- coding: utf-8 -*-
"""
Constants 模块测试
"""

import pytest

from src.constants.enums import (
    BaseEnum,
    ResponseCode,
    MessageRole,
    MediaType,
    ModelProvider,
    TaskStatus,
)
from src.constants.codes import ResponseCodeEnum, ErrorCodeEnum


class TestBaseEnum:
    """BaseEnum 基类测试"""

    def test_enum_mark_property(self):
        """测试标记属性"""
        assert ResponseCode.SUCCESS.mark == 0
        assert ResponseCode.NOT_FOUND.mark == 404

    def test_enum_value_property(self):
        """测试值属性"""
        assert ResponseCode.SUCCESS.value == "0"
        assert ResponseCode.NOT_FOUND.value == "404"

    def test_enum_desc_property(self):
        """测试描述属性"""
        assert ResponseCode.SUCCESS.desc == "Success"
        assert ResponseCode.NOT_FOUND.desc == "Not Found"

    def test_enum_str(self):
        """测试字符串表示"""
        assert str(ResponseCode.SUCCESS) == "0"
        assert str(ResponseCode.NOT_FOUND) == "404"

    def test_enum_equality(self):
        """测试相等性"""
        assert ResponseCode.SUCCESS == ResponseCode.SUCCESS
        assert ResponseCode.SUCCESS == "0"
        assert ResponseCode.SUCCESS != ResponseCode.NOT_FOUND

    def test_get_all_marks(self):
        """测试获取所有标记"""
        marks = ResponseCode.get_all_marks()
        assert 0 in marks
        assert 400 in marks
        assert 500 in marks

    def test_get_all_descs(self):
        """测试获取所有描述"""
        descs = ResponseCode.get_all_descs()
        assert "Success" in descs
        assert "Not Found" in descs

    def test_get_choices(self):
        """测试获取选择项"""
        choices = ResponseCode.get_choices()
        assert len(choices) > 0
        assert choices[0] == (0, "Success")


class TestMessageRole:
    """消息角色枚举测试"""

    def test_roles(self):
        """测试消息角色定义"""
        assert MessageRole.SYSTEM.value == "system"
        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"
        assert MessageRole.TOOL.value == "tool"


class TestMediaType:
    """媒体类型枚举测试"""

    def test_media_types(self):
        """测试媒体类型定义"""
        assert MediaType.TEXT.value == "text"
        assert MediaType.IMAGE.value == "image"
        assert MediaType.AUDIO.value == "audio"
        assert MediaType.VIDEO.value == "video"


class TestModelProvider:
    """模型提供商枚举测试"""

    def test_providers(self):
        """测试提供商定义"""
        assert ModelProvider.TONGYI.value == "tongyi"
        assert ModelProvider.DEEPSEEK.value == "deepseek"
        assert ModelProvider.GLM.value == "glm"
        assert ModelProvider.DOUBAO.value == "doubao"
        assert ModelProvider.KIMI.value == "kimi"


class TestResponseCodeEnum:
    """响应状态码枚举测试"""

    def test_success_codes(self):
        """测试成功状态码"""
        assert ResponseCodeEnum.SUCCESS == 1000

    def test_error_codes(self):
        """测试错误状态码"""
        assert ResponseCodeEnum.PARAM_ERROR == 1001
        assert ResponseCodeEnum.NOT_FOUND == 1005

    def test_chat_codes(self):
        """测试对话相关状态码"""
        assert ResponseCodeEnum.CHAT_SESSION_NOT_FOUND == 2001
        assert ResponseCodeEnum.CHAT_MESSAGE_TOO_LONG == 2002

    def test_db_codes(self):
        """测试数据库相关状态码"""
        assert ResponseCodeEnum.DB_CONNECTION_FAILED == 7001
        assert ResponseCodeEnum.DB_QUERY_FAILED == 7002
