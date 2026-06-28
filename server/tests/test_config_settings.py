# -*- coding: utf-8 -*-
"""
Settings 配置模块单元测试
"""

from src.config.settings import Settings


class TestSettingsInit:
    """Settings 初始化测试"""

    def test_default_values(self, empty_settings):
        s = empty_settings
        assert s.ALIYUN_API_KEY == ""
        assert s.ALIYUN_API_BASE == "https://dashscope.aliyuncs.com/compatible-mode/v1"
        assert s.ALIYUN_MODEL_NAME == "qwen-plus"
        assert s.DEEPSEEK_API_KEY == ""
        assert s.DEEPSEEK_MODEL_NAME == "deepseek-chat"
        assert s.GLM_MODEL_NAME == "glm-4"
        assert s.KIMI_MODEL_NAME == "moonshot-v1-8k"
        assert s.MILVUS_HOST == "192.168.21.254"
        assert s.MILVUS_PORT == 19530
        assert s.MYSQL_HOST == "127.0.0.1"
        assert s.MYSQL_PORT == 3306
        assert s.STORAGE_TYPE == "local"

    def test_custom_values(self, monkeypatch):
        monkeypatch.setenv("ALIYUN_API_KEY", "my-key")
        monkeypatch.setenv("DEEPSEEK_API_KEY", "ds-key")
        monkeypatch.setenv("MILVUS_HOST", "10.0.0.1")
        monkeypatch.setenv("MYSQL_HOST", "db.local")

        s = Settings()
        assert s.ALIYUN_API_KEY == "my-key"
        assert s.DEEPSEEK_API_KEY == "ds-key"
        assert s.MILVUS_HOST == "10.0.0.1"
        assert s.MYSQL_HOST == "db.local"

    def test_dashscope_key_fallback(self, monkeypatch):
        """DASHSCOPE_API_KEY 应作为 ALIYUN_API_KEY 的回退"""
        monkeypatch.setenv("DASHSCOPE_API_KEY", "dash-key")
        monkeypatch.delenv("ALIYUN_API_KEY", raising=False)
        s = Settings()
        assert s.ALIYUN_API_KEY == "dash-key"

    def test_temperature_parsing(self, monkeypatch):
        monkeypatch.setenv("TEMPERATURE", "0.7")
        s = Settings()
        assert s.TEMPERATURE == 0.7

    def test_temperature_invalid(self, monkeypatch):
        monkeypatch.setenv("TEMPERATURE", "not-a-number")
        s = Settings()
        assert s.TEMPERATURE == 0.0


class TestDatabaseURL:
    """数据库 URL 属性测试"""

    def test_database_url(self, empty_settings):
        s = empty_settings
        assert "mysql+pymysql" in s.DATABASE_URL
        assert s.MYSQL_HOST in s.DATABASE_URL
        assert s.MYSQL_DATABASE in s.DATABASE_URL

    def test_async_database_url(self, empty_settings):
        s = empty_settings
        assert "mysql+aiomysql" in s.ASYNC_DATABASE_URL


class TestValidateModelConfig:
    """validate_model_config 测试"""

    def test_tongyi_valid(self, fake_settings):
        assert fake_settings.validate_model_config("tongyi") is True

    def test_tongyi_missing_key(self, empty_settings):
        assert empty_settings.validate_model_config("tongyi") is False

    def test_mock_always_valid(self, empty_settings):
        assert empty_settings.validate_model_config("mock") is True

    def test_unknown_provider(self, fake_settings):
        assert fake_settings.validate_model_config("unknown_llm") is False

    def test_deepseek_valid(self, fake_settings):
        assert fake_settings.validate_model_config("deepseek") is True

    def test_glm_valid(self, fake_settings):
        assert fake_settings.validate_model_config("glm") is True

    def test_doubao_valid(self, fake_settings):
        """fake_settings 同时配置了 key 和 model_name"""
        assert fake_settings.validate_model_config("doubao") is True


class TestGetAvailableProviders:
    """get_available_providers 测试"""

    def test_returns_five_providers(self, fake_settings):
        providers = fake_settings.get_available_providers()
        assert len(providers) == 5
        names = [p["name"] for p in providers]
        assert "tongyi" in names
        assert "deepseek" in names

    def test_available_flag(self, fake_settings):
        providers = fake_settings.get_available_providers()
        tongyi = next(p for p in providers if p["name"] == "tongyi")
        assert tongyi["available"] is True

    def test_all_unavailable(self, empty_settings):
        providers = empty_settings.get_available_providers()
        assert all(not p["available"] for p in providers)


class TestGetDefaultProvider:
    """get_default_provider 测试"""

    def test_tongyi_first_priority(self, fake_settings):
        assert fake_settings.get_default_provider() == "tongyi"

    def test_fallback_to_tongyi_when_none_available(self, empty_settings):
        """没有任何配置时仍然返回 tongyi"""
        assert empty_settings.get_default_provider() == "tongyi"

    def test_fallback_to_deepseek(self, monkeypatch):
        """tongyi 不可用时回退到 deepseek"""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "ds-key")
        # 确保 tongyi 不可用
        monkeypatch.delenv("ALIYUN_API_KEY", raising=False)
        monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
        s = Settings()
        assert s.get_default_provider() == "deepseek"
