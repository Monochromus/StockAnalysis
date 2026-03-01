from __future__ import annotations
from typing import Optional
from fastapi import HTTPException, status


class TickerNotFoundError(HTTPException):
    def __init__(self, symbol: str, suggestion: Optional[str] = None):
        detail = f"Ticker '{symbol}' not found"
        if suggestion:
            detail += f". Did you mean '{suggestion}'?"
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class InsufficientDataError(HTTPException):
    def __init__(self, symbol: str, received: int, required: int = 50):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Insufficient data for '{symbol}': received {received} bars, need at least {required}"
        )


class DataProviderError(HTTPException):
    def __init__(self, message: str = "Failed to fetch data from provider"):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=message
        )


class NoPatternFoundError(HTTPException):
    def __init__(self, symbol: str, suggestion: str = "Try adjusting the zigzag threshold"):
        super().__init__(
            status_code=status.HTTP_200_OK,  # Not an error, just no pattern
            detail={"message": f"No Elliott Wave pattern detected for '{symbol}'", "suggestion": suggestion}
        )


class LowLiquidityWarning(Exception):
    """Warning for low liquidity instruments - not an HTTP exception"""
    def __init__(self, symbol: str, avg_volume: float):
        self.symbol = symbol
        self.avg_volume = avg_volume
        self.message = f"Low liquidity warning for '{symbol}': average volume {avg_volume:,.0f}"
        super().__init__(self.message)
