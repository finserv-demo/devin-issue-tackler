"""Dashboard API: Settings endpoints.

These endpoints serve and update system configuration.
In Phase 3, settings are stored in memory (no database yet).
"""

import logging

from fastapi import APIRouter

from orchestrator.config import Settings
from orchestrator.schemas.api import SettingsResponse, SettingsUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])

# In-memory settings instance (replaced by DB in production)
_settings = Settings()


@router.get("")
async def get_settings() -> SettingsResponse:
    """Get current system settings."""
    return SettingsResponse(
        opt_out_label=_settings.opt_out_label,
        acu_limit_triage=_settings.acu_limit_triage,
        acu_limit_implement=_settings.acu_limit_implement,
        max_concurrent_implement=_settings.max_concurrent_implement,
        max_concurrent_total=_settings.max_concurrent_total,
        polling_interval_seconds=_settings.polling_interval_seconds,
        bulk_triage_rate_limit=_settings.bulk_triage_rate_limit,
        target_repo=_settings.target_repo,
    )


@router.put("")
async def update_settings(update: SettingsUpdate) -> SettingsResponse:
    """Update system settings."""
    global _settings

    # Apply non-None fields from update
    current = _settings.model_dump()
    update_data = update.model_dump(exclude_none=True)
    current.update(update_data)
    _settings = Settings(**current)

    logger.info("Settings updated: %s", update_data)
    return await get_settings()
