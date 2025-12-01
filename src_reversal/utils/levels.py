"""Support and resistance level detection."""

from dataclasses import dataclass
from enum import Enum


class LevelType(Enum):
    """Type of price level."""

    SUPPORT = "support"
    RESISTANCE = "resistance"


@dataclass
class PriceLevel:
    """A detected support or resistance level."""

    price: float
    level_type: LevelType
    touches: int  # Number of times price touched this level
    strength: float  # 0-1 strength score
    timeframe: str = ""  # Optional: which timeframe this came from


def find_swing_highs(
    highs: list[float],
    window: int = 3,
) -> list[tuple[int, float]]:
    """Find swing high points (local maxima).

    A swing high is a high that is higher than `window` bars on each side.

    Args:
        highs: List of high prices.
        window: Number of bars on each side to compare.

    Returns:
        List of (index, price) tuples for swing highs.
    """
    swing_highs = []

    for i in range(window, len(highs) - window):
        is_swing = True
        for j in range(1, window + 1):
            if highs[i] <= highs[i - j] or highs[i] <= highs[i + j]:
                is_swing = False
                break

        if is_swing:
            swing_highs.append((i, highs[i]))

    return swing_highs


def find_swing_lows(
    lows: list[float],
    window: int = 3,
) -> list[tuple[int, float]]:
    """Find swing low points (local minima).

    A swing low is a low that is lower than `window` bars on each side.

    Args:
        lows: List of low prices.
        window: Number of bars on each side to compare.

    Returns:
        List of (index, price) tuples for swing lows.
    """
    swing_lows = []

    for i in range(window, len(lows) - window):
        is_swing = True
        for j in range(1, window + 1):
            if lows[i] >= lows[i - j] or lows[i] >= lows[i + j]:
                is_swing = False
                break

        if is_swing:
            swing_lows.append((i, lows[i]))

    return swing_lows


def cluster_levels(
    levels: list[tuple[int, float]],
    threshold_pct: float = 0.5,
) -> list[tuple[float, int]]:
    """Cluster nearby price levels together.

    Groups levels that are within threshold_pct of each other and counts touches.

    Args:
        levels: List of (index, price) tuples.
        threshold_pct: Percentage threshold for clustering (0.5 = 0.5%).

    Returns:
        List of (average_price, touch_count) tuples, sorted by touch count.
    """
    if not levels:
        return []

    # Sort by price
    sorted_levels = sorted(levels, key=lambda x: x[1])

    clusters = []
    current_cluster = [sorted_levels[0]]

    for i in range(1, len(sorted_levels)):
        _, prev_price = sorted_levels[i - 1]
        _, curr_price = sorted_levels[i]

        # Check if within threshold
        pct_diff = abs(curr_price - prev_price) / prev_price * 100

        if pct_diff <= threshold_pct:
            current_cluster.append(sorted_levels[i])
        else:
            # Save current cluster and start new one
            if current_cluster:
                avg_price = sum(p for _, p in current_cluster) / len(current_cluster)
                clusters.append((avg_price, len(current_cluster)))
            current_cluster = [sorted_levels[i]]

    # Don't forget last cluster
    if current_cluster:
        avg_price = sum(p for _, p in current_cluster) / len(current_cluster)
        clusters.append((avg_price, len(current_cluster)))

    # Sort by touch count descending
    clusters.sort(key=lambda x: x[1], reverse=True)

    return clusters


def detect_support_resistance(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    current_price: float | None = None,
    swing_window: int = 3,
    cluster_threshold: float = 0.5,
    min_touches: int = 2,
    max_levels: int = 5,
) -> list[PriceLevel]:
    """Detect significant support and resistance levels.

    Args:
        highs: List of high prices.
        lows: List of low prices.
        closes: List of close prices.
        current_price: Current price (uses last close if None).
        swing_window: Window size for swing detection.
        cluster_threshold: Percentage threshold for clustering.
        min_touches: Minimum touches required for a level.
        max_levels: Maximum number of levels to return.

    Returns:
        List of PriceLevel objects, sorted by proximity to current price.
    """
    if len(highs) < swing_window * 2 + 1:
        return []

    current = current_price if current_price else closes[-1]

    # Find swing points
    swing_highs = find_swing_highs(highs, swing_window)
    swing_lows = find_swing_lows(lows, swing_window)

    # Cluster levels
    resistance_clusters = cluster_levels(swing_highs, cluster_threshold)
    support_clusters = cluster_levels(swing_lows, cluster_threshold)

    levels = []

    # Process resistance levels (above current price are most relevant for pump reversals)
    max_touches_r = max((t for _, t in resistance_clusters), default=1)
    for price, touches in resistance_clusters:
        if touches >= min_touches:
            strength = touches / max_touches_r
            levels.append(
                PriceLevel(
                    price=price,
                    level_type=LevelType.RESISTANCE,
                    touches=touches,
                    strength=strength,
                )
            )

    # Process support levels
    max_touches_s = max((t for _, t in support_clusters), default=1)
    for price, touches in support_clusters:
        if touches >= min_touches:
            strength = touches / max_touches_s
            levels.append(
                PriceLevel(
                    price=price,
                    level_type=LevelType.SUPPORT,
                    touches=touches,
                    strength=strength,
                )
            )

    # Sort by proximity to current price (closest first)
    levels.sort(key=lambda x: abs(x.price - current))

    # Limit to max_levels
    return levels[:max_levels]


def find_nearest_resistance(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    current_price: float,
    max_distance_pct: float = 5.0,
) -> PriceLevel | None:
    """Find the nearest resistance level near current price.

    For pump reversals, we need to find resistance that the price is:
    - Currently AT (just reached or slightly passed)
    - Or approaching from below

    Args:
        highs: List of high prices.
        lows: List of low prices.
        closes: List of close prices.
        current_price: Current price to search from.
        max_distance_pct: Maximum distance in percent to consider (both directions).

    Returns:
        Nearest resistance level or None if not found.
    """
    levels = detect_support_resistance(
        highs=highs,
        lows=lows,
        closes=closes,
        current_price=current_price,
        swing_window=3,
        cluster_threshold=0.8,  # More lenient clustering
        min_touches=2,
        max_levels=15,
    )

    # Filter for resistance levels NEAR current price (above OR below)
    # After a pump, price may have just broken through resistance
    resistances = [
        level for level in levels
        if level.level_type == LevelType.RESISTANCE
    ]

    if not resistances:
        return None

    # Sort by absolute distance to current price (not just above)
    resistances.sort(key=lambda x: abs(x.price - current_price))

    # Get nearest that's within max distance (either direction)
    nearest = resistances[0]
    distance_pct = abs(nearest.price - current_price) / current_price * 100

    if distance_pct <= max_distance_pct:
        return nearest

    return None


def get_levels_for_chart(
    highs: list[float],
    lows: list[float],
    closes: list[float],
) -> tuple[list[float], list[float]]:
    """Get support and resistance levels formatted for charting.

    Args:
        highs: List of high prices.
        lows: List of low prices.
        closes: List of close prices.

    Returns:
        Tuple of (resistance_levels, support_levels) as price lists.
    """
    levels = detect_support_resistance(
        highs=highs,
        lows=lows,
        closes=closes,
        swing_window=3,
        cluster_threshold=0.8,  # Slightly higher for cleaner chart
        min_touches=2,
        max_levels=6,
    )

    resistance = [l.price for l in levels if l.level_type == LevelType.RESISTANCE]
    support = [l.price for l in levels if l.level_type == LevelType.SUPPORT]

    return resistance, support

