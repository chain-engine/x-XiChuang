# -*- coding: utf-8 -*-
"""
Core 模块测试
"""

import pytest

from src.core.config import Settings
from src.api.response import error_response, success_response
from src.core.exceptions import (
    AppException,
    BaseException,
    BusinessException,
    BusinessError,
    SystemException,
    SystemError,
    NotFoundError,
    ValidationError,
)
from src.schemas.common import ApiResponse, PaginatedResponse


class TestSettings:
    """Settings 配置测试"""

    def test_default_values(self, empty_settings):
        """测试默认值"""
        settings = empty_settings
        assert settings.APP_NAME == "西窗（XiChuang）"
        assert settings.APP_VERSION == "0.1.0"
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

    def test_app_exception(self):
        """测试应用异常基类"""
        exc = AppException("test error", code=500, details="detail info")
        assert exc.message == "test error"
        assert exc.code == 500
        assert exc.details == "detail info"

    def test_business_exception(self):
        """测试业务异常"""
        exc = BusinessException("validation failed", code=400)
        assert exc.message == "validation failed"
        assert exc.code == 400

    def test_system_exception(self):
        """测试系统异常"""
        exc = SystemException("system error", code=500)
        assert exc.message == "system error"
        assert exc.code == 500

    def test_backward_compat_aliases(self):
        """测试向后兼容别名"""
        assert BaseException is AppException
        assert BusinessError is BusinessException
        assert SystemError is SystemException

    def test_not_found_error(self):
        """测试未找到异常"""
        exc = NotFoundError("resource not found")
        assert exc.code == 404
        assert exc.message == "resource not found"

    def test_validation_error(self):
        """测试校验异常"""
        exc = ValidationError("invalid input")
        assert exc.code == 400


@pytest.fixture
def mock_request():
    """模拟 FastAPI Request 对象"""
    from starlette.requests import Request

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [],
    }
    request = Request(scope)
    request.state.request_id = "test-request-id"
    return request


class TestResponse:
    """响应封装测试"""

    def test_api_response(self):
        """测试统一响应模型"""
        resp = ApiResponse(code=0, message="success", data={"key": "value"})
        assert resp.code == 0
        assert resp.message == "success"
        assert resp.data == {"key": "value"}

    def test_paginated_response(self):
        """测试分页响应模型"""
        items = [{"id": i} for i in range(10)]
        paginated = PaginatedResponse.create(items=items, total=100, page=1, page_size=10)

        assert paginated.total == 100
        assert paginated.page == 1
        assert paginated.page_size == 10
        assert paginated.total_pages == 10
        assert len(paginated.items) == 10

    def test_success_response(self, mock_request):
        """测试成功响应构造"""
        resp = success_response(data={"id": 1}, request=mock_request)
        assert resp.status_code == 200
        body = resp.body.decode()
        assert '"code":200' in body
        assert '"message":"success"' in body

    def test_error_response(self, mock_request):
        """测试错误响应构造"""
        resp = error_response(request=mock_request, code=400, message="Bad request")
        assert resp.status_code == 400
        body = resp.body.decode()
        assert '"code":400' in body
        assert '"message":"Bad request"' in body
