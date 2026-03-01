import math


def calculate_retracement(start: float, end: float, current: float) -> float:
    """
    Calculate the retracement ratio of current price from start to end.

    For a move from 100 to 200, a retracement to 150 would be 0.5 (50%).

    Args:
        start: Starting price of the move
        end: Ending price of the move
        current: Current price to measure retracement

    Returns:
        Retracement ratio (0-1+), where 1.0 = 100% retracement
    """
    move = end - start
    if abs(move) < 1e-10:
        return 0.0
    retracement = end - current
    return abs(retracement / move)


def calculate_extension(wave1_start: float, wave1_end: float, wave3_end: float) -> float:
    """
    Calculate the extension ratio of wave 3 relative to wave 1.

    Args:
        wave1_start: Starting price of wave 1
        wave1_end: Ending price of wave 1
        wave3_end: Ending price of wave 3

    Returns:
        Extension ratio (e.g., 1.618 for golden ratio extension)
    """
    wave1_length = abs(wave1_end - wave1_start)
    if wave1_length < 1e-10:
        return 0.0

    # Wave 3 starts at wave 2's end (wave 1's end adjusted for wave 2)
    # For simplicity, we measure from wave 1's end
    wave3_length = abs(wave3_end - wave1_end)
    return wave3_length / wave1_length


def gaussian_score(actual: float, expected: float, sigma: float = 0.05) -> float:
    """
    Calculate a Gaussian-based score for how close actual is to expected.

    Args:
        actual: The actual measured ratio
        expected: The expected (ideal) ratio
        sigma: Standard deviation for the Gaussian (controls tolerance)

    Returns:
        Score from 0-100, where 100 is a perfect match
    """
    deviation = abs(actual - expected)
    score = math.exp(-0.5 * (deviation / sigma) ** 2) * 100
    return round(score, 2)


def percent_change(start: float, end: float) -> float:
    """
    Calculate percentage change from start to end.

    Args:
        start: Starting value
        end: Ending value

    Returns:
        Percentage change (e.g., 0.10 for 10% increase)
    """
    if abs(start) < 1e-10:
        return 0.0
    return (end - start) / start


def wave_length(start_price: float, end_price: float) -> float:
    """Calculate the absolute length of a wave."""
    return abs(end_price - start_price)


def is_upward_wave(start_price: float, end_price: float) -> bool:
    """Check if a wave moves upward."""
    return end_price > start_price


def is_downward_wave(start_price: float, end_price: float) -> bool:
    """Check if a wave moves downward."""
    return end_price < start_price
