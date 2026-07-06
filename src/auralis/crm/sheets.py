"""
Google Sheets CRM adapter — the v0 gspread integration, rebuilt with the
two fixes it needed: lazy initialization (v0 authenticated and opened the
sheet at import time, crashing the whole app if credentials were missing)
and honest failures (v0 printed exceptions and reported success anyway).
"""

import logging
from datetime import datetime, timezone

from auralis.config import get_settings
from auralis.crm.base import CRMAdapter, CRMWriteError
from auralis.models import CustomerProfile, Insights

logger = logging.getLogger(__name__)


class SheetsCRM(CRMAdapter):
    def __init__(self) -> None:
        self._worksheet = None  # opened on first write, not at construction

    def _get_worksheet(self):
        if self._worksheet is None:
            import gspread

            s = get_settings()
            try:
                client = gspread.service_account(filename=s.sheets_credentials_path)
                self._worksheet = client.open(s.sheets_spreadsheet_name).worksheet(
                    s.sheets_worksheet_name
                )
            except Exception as exc:
                raise CRMWriteError(
                    f"Could not open Google Sheet "
                    f"{s.sheets_spreadsheet_name!r}/{s.sheets_worksheet_name!r}: {exc}"
                ) from exc
        return self._worksheet

    def write_lead(self, customer: CustomerProfile, insights: Insights) -> None:
        try:
            self._get_worksheet().append_row(
                [
                    customer.name,
                    customer.email,
                    insights.sentiment,
                    ", ".join(insights.pain_points),
                    ", ".join(insights.intents),
                    ", ".join(insights.objections),
                    ", ".join(insights.risks),
                    ", ".join(insights.integrations),
                    insights.sales_stage,
                    ", ".join(insights.next_steps),
                    datetime.now(timezone.utc).isoformat(),
                ]
            )
            logger.info("CRM write OK | customer=%s", customer.name)
        except CRMWriteError:
            raise
        except Exception as exc:
            raise CRMWriteError(f"Sheets append failed: {exc}") from exc
