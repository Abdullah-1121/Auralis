"""
HubSpot CRM adapter — stage 3.

Intentionally a stub: the adapter interface exists so the pipeline is already
CRM-agnostic; implementing this is a bounded, isolated task.
"""

from auralis.crm.base import CRMAdapter
from auralis.models import CustomerProfile, Insights


class HubSpotCRM(CRMAdapter):
    def write_lead(self, customer: CustomerProfile, insights: Insights) -> None:
        raise NotImplementedError(
            "HubSpot adapter is planned for stage 3 — set CRM_PROVIDER=sheets or none."
        )
