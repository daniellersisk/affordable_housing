from __future__ import annotations

import pytest

from app.settings import Settings, _get_bool, _get_int, load_settings

pytestmark = pytest.mark.unit


def test_get_bool_uses_default_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FEATURE_FLAG", raising=False)
    assert _get_bool("FEATURE_FLAG", default=True) is True
    assert _get_bool("FEATURE_FLAG", default=False) is False


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on"])
def test_get_bool_parses_true_values(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("FEATURE_FLAG", value)
    assert _get_bool("FEATURE_FLAG", default=False) is True


@pytest.mark.parametrize("value", ["0", "false", "FALSE", "no", "off"])
def test_get_bool_parses_false_values(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("FEATURE_FLAG", value)
    assert _get_bool("FEATURE_FLAG", default=True) is False


def test_get_bool_raises_for_invalid_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FEATURE_FLAG", "maybe")
    with pytest.raises(ValueError, match="Invalid boolean for FEATURE_FLAG"):
        _get_bool("FEATURE_FLAG", default=True)


def test_get_int_uses_default_when_missing_or_blank(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PAGE_SIZE", raising=False)
    assert _get_int("PAGE_SIZE", default=50) == 50

    monkeypatch.setenv("PAGE_SIZE", "")
    assert _get_int("PAGE_SIZE", default=75) == 75


def test_get_int_parses_integer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAGE_SIZE", "200")
    assert _get_int("PAGE_SIZE", default=50) == 200


def test_get_int_raises_for_invalid_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAGE_SIZE", "abc")
    with pytest.raises(ValueError, match="Invalid integer for PAGE_SIZE"):
        _get_int("PAGE_SIZE", default=50)


def test_load_settings_uses_explicit_open_data_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NYC_OPEN_DATA_V1_URL", "https://example.com/custom")
    monkeypatch.setenv("NYC_OPEN_DATA_V1_BASE_URL", "https://base.example")
    monkeypatch.setenv("NYC_OPEN_DATA_V1_VIEW_ID", "abcd-1234")

    loaded = load_settings()

    assert loaded.nyc_open_data_url == "https://example.com/custom"
    assert loaded.resolved_open_data_url == "https://example.com/custom"


def test_load_settings_builds_open_data_url_from_base_and_view_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NYC_OPEN_DATA_V1_URL", "")
    monkeypatch.setenv("NYC_OPEN_DATA_V1_BASE_URL", "https://data.cityofnewyork.us")
    monkeypatch.setenv("NYC_OPEN_DATA_V1_VIEW_ID", "hg8x-zxpr")

    loaded = load_settings()

    assert (
        loaded.resolved_open_data_url
        == "https://data.cityofnewyork.us/resource/hg8x-zxpr.json"
    )


def test_load_settings_supports_legacy_open_data_env_vars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NYC_OPEN_DATA_V1_URL", raising=False)
    monkeypatch.delenv("NYC_OPEN_DATA_V1_BASE_URL", raising=False)
    monkeypatch.delenv("NYC_OPEN_DATA_V1_VIEW_ID", raising=False)
    monkeypatch.setenv("NYC_OPEN_DATA_BASE_URL", "https://legacy.example")
    monkeypatch.setenv("NYC_OPEN_DATA_VIEW_ID", "zzzz-9999")

    loaded = load_settings()
    assert loaded.resolved_open_data_url == "https://legacy.example/resource/zzzz-9999.json"


def test_load_settings_does_not_use_legacy_open_data_url_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NYC_OPEN_DATA_V1_URL", raising=False)
    monkeypatch.setenv("NYC_OPEN_DATA_URL", "https://legacy.example/override")
    monkeypatch.setenv("NYC_OPEN_DATA_BASE_URL", "https://legacy.example")
    monkeypatch.setenv("NYC_OPEN_DATA_VIEW_ID", "zzzz-9999")

    loaded = load_settings()
    assert loaded.nyc_open_data_url == ""
    assert loaded.resolved_open_data_url == "https://legacy.example/resource/zzzz-9999.json"


@pytest.mark.parametrize(
    "var_name",
    [
        "DB_POOL_SIZE",
        "DB_MAX_OVERFLOW",
        "DB_POOL_TIMEOUT_SECONDS",
        "DB_POOL_RECYCLE_SECONDS",
        "DB_CONNECT_TIMEOUT_SECONDS",
        "DB_STATEMENT_TIMEOUT_MS",
    ],
)
def test_load_settings_raises_for_invalid_db_int_settings(
    monkeypatch: pytest.MonkeyPatch, var_name: str
) -> None:
    monkeypatch.setenv(var_name, "not-an-int")
    with pytest.raises(ValueError, match=f"Invalid integer for {var_name}"):
        load_settings()


def test_load_settings_reads_environment_at_call_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    first = load_settings()
    assert first.app_env == "local"

    monkeypatch.setenv("APP_ENV", "test")
    second = load_settings()
    assert second.app_env == "test"


def test_settings_post_init_allows_blank_key_when_auth_disabled() -> None:
    Settings(api_auth_enabled=False, write_api_key="")


def test_settings_post_init_allows_key_when_auth_enabled() -> None:
    Settings(api_auth_enabled=True, write_api_key="some-key")


def test_settings_post_init_raises_when_auth_enabled_and_key_blank() -> None:
    with pytest.raises(ValueError, match="WRITE_API_KEY must be set"):
        Settings(api_auth_enabled=True, write_api_key="   ")
