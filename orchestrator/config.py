from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Orchestrator configuration loaded from environment variables."""

    # Required secrets
    github_webhook_secret: str = ""
    devin_api_key: str = ""  # cog_* service user credential
    devin_org_id: str = ""
    devin_v3_api_key: str = ""  # cog_* key for v3 API (ACU enrichment)
    github_token: str = ""  # PAT or GitHub App token

    # Target repository
    target_repo: str = "finserv-demo/finserv"

    # Concurrency limits
    max_concurrent_implement: int = 10
    max_concurrent_total: int = 20

    # Polling
    polling_interval_seconds: int = 15

    # Rate limiting
    bulk_triage_rate_limit: int = 5  # issues per minute

    # ACU budgets
    acu_limit_triage: int = 8
    acu_limit_implement: int = 50

    # Labels
    opt_out_label: str = "devin:skip"

    # Playbook IDs
    triage_playbook_id: str = ""
    implement_playbook_id: str = ""

    model_config = {"env_prefix": "", "env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}
