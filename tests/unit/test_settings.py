"""配置模型的单元测试。"""

from pydantic import ValidationError

from ashare_review.config.settings import Settings


def test_settings_use_mvp_defaults() -> None:
    settings = Settings.model_validate({})

    assert settings.business_timezone == "Asia/Shanghai"
    assert settings.storage_timezone == "UTC"
    assert settings.collection_timeout_seconds == 10.0
    assert settings.collection_max_attempts == 3
    assert settings.ai_enabled is False
    assert settings.email_enabled is False


def test_settings_reject_unknown_timezone() -> None:
    try:
        Settings.model_validate({"business_timezone": "Not/A_Timezone"})
    except ValidationError as error:
        assert "Unknown IANA timezone" in str(error)
    else:
        raise AssertionError("Expected invalid timezone to be rejected")
