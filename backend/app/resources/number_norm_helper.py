import re
from decimal import Decimal, ROUND_HALF_UP

def normalize_number(
    value,
    decimal_separator=".",
    max_decimals=2,
    strip_trailing_zeros=True,
    allow_thousands_separator=True,
):
    """
    Normalize numeric input to a uniform decimal format.

    Parameters:
        value (str | int | float): Input number (e.g., '1,234', '1.00', 1)
        decimal_separator (str): Output decimal separator (default='.')
        max_decimals (int | None): Max digits after decimal (None = no limit)
        strip_trailing_zeros (bool): Remove trailing zeros (default=True)
        allow_thousands_separator (bool): Remove thousands separators (default=True)

    Returns:
        str: Normalized number string
    """

    if value is None:
        return None

    value = str(value).strip()

    if allow_thousands_separator:
        value = re.sub(r"(?<=\d)[, ](?=\d{3}\b)", "", value)

    value = value.replace(",", ".")

    try:
        number = Decimal(value)
    except:
        return value

    if max_decimals is not None:
        quantize_str = "1." + ("0" * max_decimals)
        number = number.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)

    result = format(number, "f")

    if strip_trailing_zeros and "." in result:
        result = result.rstrip("0").rstrip(".")

    if decimal_separator != ".":
        result = result.replace(".", decimal_separator)

    return result
