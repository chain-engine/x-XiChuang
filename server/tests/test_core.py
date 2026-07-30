# -*- coding: utf-8 -*-
"""
Core 模块测试
"""

import pytest

from src.core.config import Settings
from src.core.exceptions import (
    BaseException,
    BusinessError,
    SystemError,
    NotFoundError,
    ValidationError,
)
from src.core.response import BaseResp, SuccessResp, ErrorResp, PaginatedData


class TestSettings:
    """Settings 配置测试"""

    def test_default_values(self, empty_settings):
        """测试默认值"""
        settings = empty_settings
        assert settings.APP_NAME == "西窗 XiChuang"
        assert settings.APP_VERSION == "1.0.0"
        assert settings.DEBUG is True
        assert settings.ENVIRONMENT == "development"

    def test_provider_validation(self, mock_settings):
        """测试提供商配置验证"""
        settings = mock_settings
        assert settings.validate_model_config("tongyi") is True
        assert settings.validate_model_config("deepseek") is True
        assert settings.validate_model_config("glm") is True

    def test_provider_display_name(self, mock_settings):
        """测试提供商显示名称"""
        settings = mock_settings
        assert settings.get_provider_display_name("tongyi") == "千问"
        assert settings.get_provider_display_name("deepseek") == "DeepSeek"
        assert settings.get_provider_display_name("unknown") == "未知"

    def test_provider_model_name(self, mock_settings):
        """测试提供商模型名称"""
        settings = mock_settings
        assert settings.get_provider_model_name("tongyi") == "qwen-plus"
        assert settings.get_provider_model_name("deepseek") == "deepseek-chat"

    def test_available_providers(self, mock_settings):
        """测试可用提供商列表"""
        settings = mock_settings
        providers = settings.get_available_providers()
        assert len(providers) == 5
        assert any(p["name"] == "tongyi" and p["available"] for p in providers)

    def test_default_provider(self, mock_settings):
        """测试默认提供商"""
        settings = mock_settings
        assert settings.get_default_provider() == "tongyi"

    def test_database_url(self, mock_settings):
        """测试数据库 URL"""
        settings = mock_settings
        assert "mysql" in settings.DATABASE_URL
        assert "127.0.0.1" in settings.DATABASE_URL


class TestExceptions:
    """异常测试"""

    def test_base_exception(self):
        """测试基础异常"""
        exc = BaseException("test error", code=500, detail="detail info")
        assert exc.message == "test error"
        assert exc.code == 500
        assert exc.detail == "detail info"

    def test_business_error(self):
        """测试业务异常"""
        exc = BusinessError("validation failed", code=400)
        assert exc.message == "validation failed"
        assert exc.code == 400

    def test_system_error(self):
        """测试系统异常"""
        exc = SystemError("system error", code=500)
        assert exc.message == "system error"
        assert exc.code == 500

    def test_not_found_error(self):
        """测试未找到异常"""
        exc = NotFoundError("resource not found")
        assert exc.code == 404
        assert exc.message == "resource not found"

    def test_validation_error(self):
        """测试校验异常"""
        exc = ValidationError("invalid input")
        assert exc.code == 400


class TestResponse:
    """响应封装测试"""

    def test_base_resp(self):
        """测试基础响应"""
        resp = BaseResp(code=0, message="success", data={"key": "value"})
        assert resp.code == 0
        assert resp.message == "success"
        assert resp.data == {"key": "value"}

    def test_success_resp(self):
        """测试成功响应"""
        resp = SuccessResp(data={"id": 1})
        assert resp.code == 0
        assert resp.message == "success"
        assert resp.data == {"id": 1}

    def test_error_resp(self):
        """测试错误响应"""
        resp = ErrorResp.from_exception("error occurred", code=400, detail="details")
        assert resp.code == 400
        assert resp.message == "error occurred"
        assert resp.detail == "details"

    def test_paginated_data(self):
        """测试分页数据"""
        items = [{"id": i} for i in range(10)]
        paginated = PaginatedData.create(items=items, total=100, page=1, page_size=10)

        assert paginated.total == 100
        assert paginated.page == 1
        assert paginated.page_size == 10
        assert paginated.total_pages == 10
        assert len(paginated.items) == 10
