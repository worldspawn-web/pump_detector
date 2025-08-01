import matplotlib.pyplot as plt
import os


class ChartGenerator:
    def generate_chart(self, symbol, candles):
        prices = [float(c[4]) for c in candles]
        timestamps = [c[0] for c in candles]

        plt.figure(figsize=(8, 4))
        plt.plot(prices, marker="o", linestyle="-", linewidth=2)
        plt.title(f"{symbol} - Last 10m")
        plt.grid(True)
        plt.tight_layout()

        filename = f"temp_{symbol}.png"
        filepath = os.path.join("temp", filename)
        os.makedirs("temp", exist_ok=True)
        plt.savefig(filepath)
        plt.close()

        return filepath
