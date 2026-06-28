# Fee configuration
FEE_RATE = 0.001  # 0.1% per trade


def calculate_fee(amount: float) -> float:
    """Calculate trading fee."""
    return abs(amount) * FEE_RATE
