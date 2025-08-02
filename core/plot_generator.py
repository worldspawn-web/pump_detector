import os
import pandas as pd
import mplfinance as mpf
from datetime import timedelta
import aiohttp


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
        gain = delta.clip(lower=0).rolling(window=14).mean()
        loss = (-delta.clip(upper=0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-6)
        df["RSI"] = 100 - (100 / (1 + rs))
        df["RSI"] = df["RSI"].fillna(50)

        # Минималистичная тёмная тема
        my_style = mpf.make_mpf_style(
            base_mpf_style="starsandstripes",
            rc={
                "axes.facecolor": "#181818",
                "figure.facecolor": "#181818",
                "savefig.facecolor": "#181818",
                "text.color": "#cccccc",
                "axes.labelcolor": "#888888",
                "xtick.color": "#555555",
                "ytick.color": "#555555",
                "grid.color": "#2a2a2a",
            },
            marketcolors=mpf.make_marketcolors(
                up="#26de81",
                down="#ff5252",
                edge="inherit",
                wick="#888888",
                volume="inherit",
            ),
        )

        # Уровни и RSI
        add_plot = []

        if support:
            add_plot.append(
                mpf.make_addplot(
                    [support] * len(df),
                    type="line",
                    color="#3ec1d3",
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
                    color="#f6ab6c",
                    linestyle="--",
                    width=1,
                    panel=0,
                )
            )

        add_plot.append(
            mpf.make_addplot(df["RSI"], panel=1, color="#fddb3a", width=1.5)
        )

        # Сохраняем картинку
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
            ylabel="",
            ylabel_lower="",
            datetime_format="%H:%M",
            xrotation=0,
            tight_layout=True,
            savefig=dict(fname=filepath, facecolor="#181818"),
        )

        return filepath


# Метод получения уровней с H1 (экстремумы по high/low)
async def get_hourly_levels(symbol):
    url = (
        f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval=1h&limit=100"
    )
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=10) as res:
                if res.status != 200:
                    print(f"[!] Error fetching 1h candles for {symbol}: {res.status}")
                    return None, None
                data = await res.json()
                highs = [float(c[2]) for c in data[-20:]]
                lows = [float(c[3]) for c in data[-20:]]
                return min(lows), max(highs)
        except Exception as e:
            print(f"[!] Exception fetching hourly levels: {e}")
            return None, None
