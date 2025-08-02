import os
import pandas as pd
import matplotlib.pyplot as plt
import mplfinance as mpf
from matplotlib.gridspec import GridSpec


class ChartGenerator:
    def generate_chart(self, symbol, candles):
        # Преобразуем данные в DataFrame
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
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)

        df = df[["open", "high", "low", "close", "volume"]].astype(float)

        # Рассчитаем RSI
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-6)  # избегаем деления на 0
        df["rsi"] = 100 - (100 / (1 + rs))

        # Создаём график с двумя панелями
        fig = mpf.figure(style="charles", figsize=(10, 6), dpi=100)
        fig.patch.set_facecolor("#121212")  # фон всей фигуры

        gs = GridSpec(2, 1, height_ratios=[3, 1])
        ax_main = fig.add_subplot(gs[0])
        ax_rsi = fig.add_subplot(gs[1], sharex=ax_main)

        # Рисуем свечи
        mpf.plot(
            df,
            type="candle",
            ax=ax_main,
            volume=False,
            style="charles",
            ylabel="Price",
            datetime_format="%H:%M",
        )

        # Рисуем RSI
        ax_rsi.plot(df.index, df["rsi"], color="orange", linewidth=1.2)
        ax_rsi.axhline(70, color="red", linestyle="--", linewidth=0.8)
        ax_rsi.axhline(30, color="green", linestyle="--", linewidth=0.8)
        ax_rsi.set_ylabel("RSI", color="white")
        ax_rsi.set_facecolor("#121212")
        ax_rsi.grid(True, color="#444444")

        for spine in ax_rsi.spines.values():
            spine.set_color("white")
        ax_rsi.tick_params(axis="x", colors="white")
        ax_rsi.tick_params(axis="y", colors="white")

        ax_main.set_facecolor("#121212")
        for spine in ax_main.spines.values():
            spine.set_color("white")
        ax_main.tick_params(axis="x", colors="white")
        ax_main.tick_params(axis="y", colors="white")

        # Сохраняем картинку
        filename = f"temp_{symbol}.png"
        filepath = os.path.join("temp", filename)
        os.makedirs("temp", exist_ok=True)
        plt.tight_layout()
        fig.savefig(filepath, facecolor=fig.get_facecolor())
        plt.close(fig)

        return filepath
