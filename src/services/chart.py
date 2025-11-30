"""Chart generation service for pump signals."""

import io
from typing import Any

import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt
from loguru import logger

from src.utils.indicators import calculate_rsi_series, calculate_macd


def create_dark_style() -> mpf.make_mpf_style:
    """Create a dark theme style for mplfinance."""
    mc = mpf.make_marketcolors(
        up="#26a69a",
        down="#ef5350",
        edge="inherit",
        wick="inherit",
        volume="inherit",
        ohlc="inherit",
    )

    style = mpf.make_mpf_style(
        base_mpf_style="nightclouds",
        marketcolors=mc,
        facecolor="#131722",
        edgecolor="#363a45",
        figcolor="#131722",
        gridcolor="#1e222d",
        gridstyle="-",
        y_on_right=True,
        rc={
            "axes.edgecolor": "#363a45",
            "axes.labelcolor": "#9598a1",
            "axes.labelsize": 10,
            "figure.facecolor": "#131722",
            "text.color": "#d1d4dc",
            "xtick.color": "#787b86",
            "ytick.color": "#787b86",
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "font.size": 9,
            "grid.linewidth": 0.5,
        },
    )
    return style


class ChartGenerator:
    """Generates candlestick charts with technical indicators."""

    def __init__(self) -> None:
        """Initialize the chart generator."""
        self._style = create_dark_style()

    def generate_chart(
        self,
        klines: list[dict[str, Any]],
        symbol: str,
    ) -> bytes | None:
        """Generate a candlestick chart with indicators.

        Args:
            klines: List of kline data (1H timeframe, oldest to newest).
            symbol: Trading pair symbol for the title.

        Returns:
            PNG image as bytes, or None if generation fails.
        """
        if not klines or len(klines) < 35:
            logger.warning(f"Insufficient kline data for chart: {len(klines) if klines else 0}")
            return None

        try:
            # Convert to DataFrame
            df = self._prepare_dataframe(klines)
            if df is None or len(df) < 35:
                return None

            # Calculate indicators
            closes = df["Close"].tolist()
            rsi_values = calculate_rsi_series(closes, period=14)
            macd_line, signal_line, histogram = calculate_macd(closes)

            # Add indicators to dataframe
            df["RSI"] = rsi_values
            df["MACD"] = macd_line
            df["Signal"] = signal_line
            df["Histogram"] = histogram

            # Generate chart
            return self._render_chart(df, symbol)

        except Exception as e:
            logger.error(f"Failed to generate chart for {symbol}: {e}")
            return None

    def _prepare_dataframe(self, klines: list[dict]) -> pd.DataFrame | None:
        """Convert klines to pandas DataFrame for mplfinance."""
        try:
            data = []
            for k in klines:
                data.append({
                    "Date": pd.to_datetime(k["time"], unit="ms"),
                    "Open": float(k["open"]),
                    "High": float(k["high"]),
                    "Low": float(k["low"]),
                    "Close": float(k["close"]),
                    "Volume": float(k.get("volume", 0)),
                })

            df = pd.DataFrame(data)
            df.set_index("Date", inplace=True)
            df.sort_index(inplace=True)

            return df

        except Exception as e:
            logger.error(f"Failed to prepare dataframe: {e}")
            return None

    def _render_chart(self, df: pd.DataFrame, symbol: str) -> bytes | None:
        """Render the chart to PNG bytes."""
        try:
            # Create additional plots for RSI and MACD
            # RSI panel
            rsi_plot = mpf.make_addplot(
                df["RSI"],
                panel=2,
                color="#b39ddb",
                ylabel="RSI",
                ylim=(0, 100),
                secondary_y=False,
            )

            # RSI levels (30 and 70)
            df["RSI_30"] = 30
            df["RSI_70"] = 70
            rsi_30_plot = mpf.make_addplot(
                df["RSI_30"],
                panel=2,
                color="#4caf50",
                linestyle="--",
                width=0.7,
                secondary_y=False,
            )
            rsi_70_plot = mpf.make_addplot(
                df["RSI_70"],
                panel=2,
                color="#f44336",
                linestyle="--",
                width=0.7,
                secondary_y=False,
            )

            # MACD panel
            macd_plot = mpf.make_addplot(
                df["MACD"],
                panel=3,
                color="#2196f3",
                ylabel="MACD",
                secondary_y=False,
            )
            signal_plot = mpf.make_addplot(
                df["Signal"],
                panel=3,
                color="#ff9800",
                secondary_y=False,
            )

            # MACD Histogram
            hist_colors = [
                "#26a69a" if v >= 0 else "#ef5350"
                for v in df["Histogram"].fillna(0)
            ]
            histogram_plot = mpf.make_addplot(
                df["Histogram"],
                panel=3,
                type="bar",
                color=hist_colors,
                secondary_y=False,
                width=0.7,
            )

            # Combine all additional plots
            add_plots = [
                rsi_plot, rsi_30_plot, rsi_70_plot,
                macd_plot, signal_plot, histogram_plot,
            ]

            # Create figure
            fig, axes = mpf.plot(
                df,
                type="candle",
                style=self._style,
                title=f"\n{symbol} (1H)",
                ylabel="Price",
                volume=True,
                volume_panel=1,
                addplot=add_plots,
                panel_ratios=(3, 1, 1, 1),  # Price, Volume, RSI, MACD
                figsize=(12, 10),
                tight_layout=True,
                returnfig=True,
                datetime_format="%m-%d %H:%M",
                xrotation=0,
            )

            # Save to bytes
            buf = io.BytesIO()
            fig.savefig(
                buf,
                format="png",
                dpi=150,
                bbox_inches="tight",
                facecolor="#131722",
                edgecolor="none",
            )
            buf.seek(0)
            plt.close(fig)

            return buf.getvalue()

        except Exception as e:
            logger.error(f"Failed to render chart: {e}")
            return None
