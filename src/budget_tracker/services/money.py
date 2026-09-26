from decimal import Decimal, InvalidOperation


def parse_cents(text: str) -> int:
    """Parse a user- or bank-style amount into integer cents.

    "12.5" -> 1250, "$1,234.56" -> 123456, "-3" -> -300, "(5.00)" -> -500.
    Raises ValueError for anything else, including fractions of a cent.
    """
    s = text.strip().replace("$", "").replace(",", "")
    negative = s.startswith("(") and s.endswith(")")
    if negative:
        s = s[1:-1]
    try:
        d = Decimal(s)
    except InvalidOperation:
        raise ValueError(f"Not a valid amount: {text!r}") from None
    if not d.is_finite() or d.as_tuple().exponent < -2:
        raise ValueError(f"Not a valid amount: {text!r}")
    cents = int(d * 100)
    return -cents if negative else cents


def format_cents(cents: int) -> str:
    """1234 -> "$12.34", -123456 -> "-$1,234.56"."""
    sign = "-" if cents < 0 else ""
    dollars, rem = divmod(abs(cents), 100)
    return f"{sign}${dollars:,}.{rem:02}"
