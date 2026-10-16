from decimal import Decimal

ROUNDING_TOLERANCE = Decimal("1")


def amounts_differ(first: Decimal, second: Decimal) -> bool:
    return abs(first - second) > ROUNDING_TOLERANCE


def format_pesos(amount: Decimal) -> str:
    return f"{amount:,.0f}".replace(",", ".")
