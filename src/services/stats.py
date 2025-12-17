"""Statistics formatting service."""

from datetime import datetime, timezone, timedelta

from src.database.db import Database
from src.database.models import CoinStats


# UTC+3 timezone
UTC_PLUS_3 = timezone(timedelta(hours=3))


class StatsFormatter:
    """Formats statistics for Telegram display."""

    def __init__(self, database: Database) -> None:
        """Initialize the formatter.

        Args:
            database: Database instance.
        """
        self._db = database

    async def format_global_stats_message(self) -> str:
        """Format the global stats pinned message.

        Returns:
            Formatted message string.
        """
        stats = await self._db.get_global_stats()
        now = datetime.now(UTC_PLUS_3)

        # Format average time
        avg_time = "N/A"
        if stats.avg_time_to_50pct_seconds:
            hours = stats.avg_time_to_50pct_seconds / 3600
            if hours < 1:
                avg_time = f"{stats.avg_time_to_50pct_seconds / 60:.0f}m"
            else:
                avg_time = f"{hours:.1f}h"

        lines = [
            "📊 <b>PUMP REVERSAL STATISTICS</b>",
            f"<i>Last Updated: {now.strftime('%H:%M')} (UTC+3)</i>",
            "",
            "━━━ <b>All-Time Performance</b> ━━━",
            "",
            f"📈 Total Pumps Tracked: <b>{stats.total_pumps}</b>",
            f"🔄 Active Monitoring: <b>{stats.active_monitoring}</b>",
            "",
        ]

        # Only show rates if we have completed pumps
        completed = stats.total_pumps - stats.active_monitoring
        if completed > 0:
            # Format average time to 100%
            avg_time_100 = "N/A"
            if stats.avg_time_to_100pct_seconds:
                hours_100 = stats.avg_time_to_100pct_seconds / 3600
                if hours_100 < 1:
                    avg_time_100 = f"{stats.avg_time_to_100pct_seconds / 60:.0f}m"
                else:
                    avg_time_100 = f"{hours_100:.1f}h"

            lines.extend(
                [
                    f"✅ 50% Retrace Rate: <b>{stats.pct_hit_50pct:.0f}%</b>",
                    f"⏱️ Avg Time to 50%: <b>{avg_time}</b>",
                    f"🎯 Full Reversal Rate: <b>{stats.pct_full_reversal:.0f}%</b>",
                    f"⏱️ Avg Time to 100%: <b>{avg_time_100}</b>",
                    "",
                ]
            )

        # Top performers - show if at least 3 coins have history
        if stats.top_coins and len(stats.top_coins) >= 3:
            lines.append("━━━ <b>Top Reversal Coins</b> ━━━")
            lines.append("")
            for i, (symbol, rate, count) in enumerate(stats.top_coins[:5], start=1):
                coin_name = symbol.replace("_USDT", "")
                lines.append(f"{i}. {coin_name} - <b>{rate:.0f}%</b> ({count} pumps)")
            lines.append("")

        # Worst performers
        if stats.worst_coins:
            lines.append("━━━ <b>Avoid These</b> ━━━")
            lines.append("")
            for i, (symbol, rate, count) in enumerate(stats.worst_coins[:3], start=1):
                coin_name = symbol.replace("_USDT", "")
                lines.append(f"⚠️ {coin_name} - <b>{rate:.0f}%</b> ({count} pumps)")
            lines.append("")

        # Today's stats
        lines.append("━━━ <b>Today's Results</b> ━━━")
        lines.append("")
        if stats.today_pumps > 0 or stats.active_monitoring > 0:
            if stats.today_pumps > 0:
                lines.append(f"📊 Detected today: <b>{stats.today_pumps}</b>")

            if stats.active_monitoring > 0:
                lines.append(f"🔄 Being tracked: <b>{stats.active_monitoring}</b>")
        else:
            lines.append("<i>No pumps recorded today</i>")

        return "\n".join(lines)

    def format_coin_history_section(
        self,
        stats: CoinStats,
        last_results: list[bool],
    ) -> str:
        """Format the reversal history section for a pump signal.

        Args:
            stats: Coin statistics.
            last_results: List of last N results (True = success).

        Returns:
            Formatted section string.
        """
        lines = [
            f"━━━ <b>Reversal History ({stats.total_pumps} pumps)</b> ━━━",
            "",
            f"⏱️ Time to 50%: <b>{stats.avg_time_to_50pct_formatted}</b> ({stats.pct_hit_50pct:.0f}% hit)",
            f"⏱️ Time to 100%: <b>{stats.avg_time_to_100pct_formatted}</b> ({stats.pct_full_reversal:.0f}% hit)",
            f"📉 Max Drop: <b>-{stats.avg_max_drop_from_high:.1f}%</b> avg",
            f"🎯 Full Reversal: <b>{stats.pct_full_reversal:.0f}%</b> of pumps",
        ]

        # Last 5 results
        if last_results:
            results_str = "".join("✅" if r else "❌" for r in last_results)
            lines.append(f"📊 Last {len(last_results)}: {results_str}")

        # Reliability
        lines.append(f"{stats.reliability_emoji} Reliability")

        return "\n".join(lines)

    def format_no_history_section(self) -> str:
        """Format section when no history is available.

        Returns:
            Formatted section string.
        """
        return (
            "━━━ <b>Reversal History</b> ━━━\n"
            "\n"
            "🆕 First recorded pump - no history yet"
        )
