"""Helpers for comparing and displaying money amounts (Colombian pesos)."""
from decimal import Decimal

ROUNDING_TOLERANCE = Decimal("1")


def amounts_differ(first: Decimal, second: Decimal) -> bool:
    return abs(first - second) > ROUNDING_TOLERANCE


def format_pesos(amount: Decimal) -> str:
    """Formats 1234567 as '1.234.567' (Colombian thousands separator)."""
    return f"{amount:,.0f}".replace(",", ".")
