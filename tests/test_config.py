
import pytest

from orchestrator.config import Settings


def test_settings_defaults() -> None:
    """Settings should have sensible defaults for optional fields."""
    settings = Settings()
    assert settings.target_repo == "finserv-demo/finserv"
    assert settings.max_concurrent_implement == 10
    assert settings.max_concurrent_total == 20
    assert settings.polling_interval_seconds == 15
    assert settings.bulk_triage_rate_limit == 5
    assert settings.acu_limit_triage == 8
    assert settings.acu_limit_implement == 50
    assert settings.opt_out_label == "devin:skip"


def test_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings should read from environment variables."""
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test123")
    monkeypatch.setenv("DEVIN_API_KEY", "cog_test456")
    monkeypatch.setenv("DEVIN_ORG_ID", "org-test789")
    monkeypatch.setenv("TARGET_REPO", "myorg/myrepo")
    monkeypatch.setenv("MAX_CONCURRENT_IMPLEMENT", "5")

    settings = Settings()
    assert settings.github_token == "ghp_test123"
    assert settings.devin_api_key == "cog_test456"
    assert settings.devin_org_id == "org-test789"
    assert settings.target_repo == "myorg/myrepo"
    assert settings.max_concurrent_implement == 5
