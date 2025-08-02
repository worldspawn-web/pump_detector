import os
import pandas as pd
import mplfinance as mpf
from datetime import timedelta
import matplotlib.pyplot as plt


class ChartGenerator:
    def generate_chart(self, symbol, candles, support=None, resistance=None):
        # DataFrame из свечей
        df = pd.DataFrame(
            candles,
            columns=[
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "_",
                "_",
                "_",
                "_",
                "_",
                "_",
            ],
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms") + timedelta(
            hours=3
        )
        df.set_index("timestamp", inplace=True)
        df = df[["open", "high", "low", "close", "volume"]].astype(float)

        # RSI
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-6)
        df["RSI"] = 100 - (100 / (1 + rs))

        # Стиль
        my_style = mpf.make_mpf_style(
            base_mpf_style="charles",
            rc={"axes.facecolor": "#121212", "figure.facecolor": "#121212"},
            marketcolors=mpf.make_marketcolors(
                up="green",
                down="red",
                edge="i",
                wick="i",
                volume="in",
            ),
        )

        # Уровни
        add_plot = []

        if support:
            add_plot.append(
                mpf.make_addplot(
                    [support] * len(df),
                    type="line",
                    color="cyan",
                    linestyle="--",
                    width=1,
                    panel=0,
                )
            )
        if resistance:
            add_plot.append(
                mpf.make_addplot(
                    [resistance] * len(df),
                    type="line",
                    color="orange",
                    linestyle="--",
                    width=1,
                    panel=0,
                )
            )

        # RSI plot
        add_plot.append(mpf.make_addplot(df["RSI"], panel=1, color="yellow", width=1.5))

        # График
        filename = f"temp_{symbol}.png"
        filepath = os.path.join("temp", filename)
        os.makedirs("temp", exist_ok=True)

        mpf.plot(
            df,
            type="candle",
            addplot=add_plot,
            style=my_style,
            figsize=(10, 6),
            panel_ratios=(3, 1),
            ylabel="Price",
            ylabel_panel=1,
            savefig=dict(fname=filepath, facecolor="#121212"),
        )

        return filepath
