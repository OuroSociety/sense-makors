from decimal import Decimal
from typing import Union

def safe_decimal_mul(*args: Union[Decimal, float, str]) -> Decimal:
    """Safely multiply numbers, converting to Decimal as needed"""
    result = Decimal("1")
    for arg in args:
        if isinstance(arg, float):
            result *= Decimal(str(arg))
        elif isinstance(arg, str):
            result *= Decimal(arg)
        else:
            result *= arg
    return result 