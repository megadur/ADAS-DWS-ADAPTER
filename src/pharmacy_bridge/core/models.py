"""
Pharmacy Core v0.1 Data Models
Standardized, vendor-neutral telemetry and liquidity models.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from ..adas_parser import ADASMetrics
from ..wwks2_bridge import WWKS2TelemetryTracker


@dataclass
class FinanceLiquidityMetrics:
    """7-Day Liquidity Forecast Model for Apotheke Core."""
    bank_balance_cents: int = 12000000          # 120,000.00 €
    arz_receivables_7d_cents: int = 14500000    # +145,000.00 € expected ARZ payout
    wholesaler_payables_7d_cents: int = 19000000# -190,000.00 € due to wholesaler
    other_expenses_7d_cents: int = 3500000      # -35,000.00 € fixed costs/payroll
    warning_threshold_cents: int = 2500000      # Warning if 7d projected < 25,000 €

    @property
    def projected_liquidity_7d_cents(self) -> int:
        """Calculates 7-day projected liquidity in cents."""
        return (
            self.bank_balance_cents
            + self.arz_receivables_7d_cents
            - self.wholesaler_payables_7d_cents
            - self.other_expenses_7d_cents
        )

    @property
    def bank_balance_eur(self) -> float:
        return round(self.bank_balance_cents / 100.0, 2)

    @property
    def arz_receivables_7d_eur(self) -> float:
        return round(self.arz_receivables_7d_cents / 100.0, 2)

    @property
    def wholesaler_payables_7d_eur(self) -> float:
        return round(self.wholesaler_payables_7d_cents / 100.0, 2)

    @property
    def other_expenses_7d_eur(self) -> float:
        return round(self.other_expenses_7d_cents / 100.0, 2)

    @property
    def projected_liquidity_7d_eur(self) -> float:
        return round(self.projected_liquidity_7d_cents / 100.0, 2)

    @property
    def is_liquidity_warning(self) -> bool:
        return self.projected_liquidity_7d_cents < self.warning_threshold_cents

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bank_balance_cents": self.bank_balance_cents,
            "bank_balance_eur": self.bank_balance_eur,
            "arz_receivables_7d_cents": self.arz_receivables_7d_cents,
            "arz_receivables_7d_eur": self.arz_receivables_7d_eur,
            "wholesaler_payables_7d_cents": self.wholesaler_payables_7d_cents,
            "wholesaler_payables_7d_eur": self.wholesaler_payables_7d_eur,
            "other_expenses_7d_cents": self.other_expenses_7d_cents,
            "other_expenses_7d_eur": self.other_expenses_7d_eur,
            "projected_liquidity_7d_cents": self.projected_liquidity_7d_cents,
            "projected_liquidity_7d_eur": self.projected_liquidity_7d_eur,
            "is_liquidity_warning": self.is_liquidity_warning,
            "ts": datetime.now(timezone.utc).isoformat()
        }


@dataclass
class PharmacyCoreMetrics:
    """Unified Pharmacy Core Data Object."""
    finance: FinanceLiquidityMetrics = field(default_factory=FinanceLiquidityMetrics)
    data_quality: str = "complete"
    last_update_iso: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
