def subtotal(prices: list[float]) -> float:
    return round(sum(prices), 2)


def discount(total: float, percent: int) -> float:
    return round(total * (100 - percent) / 100, 2)


def with_tax(total: float, rate: float = 0.2) -> float:
    return round(total * (1 + rate), 2)
