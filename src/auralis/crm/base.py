"""
CRM adapter interface — the pipeline talks to this, never to a vendor SDK.

Swapping Google Sheets for HubSpot (or anything else) is a config change:
set CRM_PROVIDER in .env and implement write_lead().
"""

from abc import ABC, abstractmethod

from auralis.config import get_settings
from auralis.models import CustomerProfile, Insights


class CRMWriteError(RuntimeError):
    """Raised when a CRM write fails — loudly, never swallowed."""


class CRMAdapter(ABC):
    @abstractmethod
    def write_lead(self, customer: CustomerProfile, insights: Insights) -> None:
        """Persist one lead. Raise CRMWriteError on failure."""


def get_crm_adapter() -> CRMAdapter | None:
    """Return the configured adapter, or None when CRM is disabled."""
    provider = get_settings().crm_provider.lower()
    if provider in ("", "none"):
        return None
    if provider == "sheets":
        from auralis.crm.sheets import SheetsCRM

        return SheetsCRM()
    if provider == "hubspot":
        from auralis.crm.hubspot import HubSpotCRM

        return HubSpotCRM()
    raise ValueError(f"Unknown CRM_PROVIDER: {provider!r} (use none|sheets|hubspot)")
