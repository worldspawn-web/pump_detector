import os
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
from config import PLOT_DIR
from utils import logger

# Создаём директорию для графиков
os.makedirs(PLOT_DIR, exist_ok=True)

def calculate_rsi(series, window=14):
    """Расчёт RSI для серии цен."""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(series, fast=12, slow=26, signal=9):
    """Расчёт MACD и сигнальной линии."""
    exp1 = series.ewm(span=fast).mean()
    exp2 = series.ewm(span=slow).mean()
    macd_line = exp1 - exp2
    signal_line = macd_line.ewm(span=signal).mean()
    return macd_line, signal_line

def add_fibonacci_levels(ax, low, high):
    """Уровни Фибоначчи."""
    levels = [0, 0.236, 0.382, 0.5, 0.618, 1]
    colors = ['gray', 'blue', 'green', 'orange', 'red', 'purple']
    for i, level in enumerate(levels):
        price = low + (high - low) * level
        ax.axhline(price, color=colors[i], linestyle='--', alpha=0.7, label=f'Fib {level}')
    ax.legend(loc='upper left', fontsize='x-small')

def plot_1min_candlestick_chart(symbol: str, ohlcv_data) -> str:
    """Построить 1-минутный график в виде японских свечей."""
    try:
        df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        fig, ax = plt.subplots(figsize=(12, 6))
        colors = ['green' if close > open else 'red' for open, close in zip(df['open'], df['close'])]

        # Свечи: тело + тени
        for i, row in df.iterrows():
            # Тело свечи
            body_height = abs(row['close'] - row['open'])
            body_start = min(row['open'], row['close'])
            ax.bar(row['timestamp'], body_height, bottom=body_start, width=0.001, color=colors[i], edgecolor='black')

            # Тени
            wick_high = max(row['high'], row['close'], row['open'])
            wick_low = min(row['low'], row['close'], row['open'])
            ax.vlines(row['timestamp'], wick_low, wick_high, color=colors[i], linewidth=0.8)

        ax.set_title(f"{symbol} — 1 Minute Candlestick Chart", fontsize=14)
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(DateFormatter('%H:%M'))
        plt.xticks(rotation=45)
        plt.tight_layout()

        filepath = os.path.join(PLOT_DIR, f"{symbol.replace('/', '_')}_1m.png")
        plt.savefig(filepath, dpi=100, bbox_inches='tight')
        plt.close()

        logger.info(f"1m candlestick chart saved: {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"Error plotting 1m candlestick chart for {symbol}: {e}")
        return None

def plot_1h_candlestick_chart_with_indicators(symbol: str, ohlcv_data) -> str:
    """Построить 1-часовой график в виде японских свечей + RSI + MACD."""
    try:
        df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        # MACD
        exp1 = df['close'].ewm(span=12).mean()
        exp2 = df['close'].ewm(span=26).mean()
        macd_line = exp1 - exp2
        signal_line = macd_line.ewm(span=9).mean()

        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10), height_ratios=[3, 1, 1])

        # Свечи на 1h
        colors = ['green' if close > open else 'red' for open, close in zip(df['open'], df['close'])]
        for i, row in df.iterrows():
            ax1.vlines(row['timestamp'], row['low'], row['high'], color=colors[i], linewidth=0.8)
            ax1.plot([row['timestamp'], row['timestamp']], [row['open'], row['close']],
                     color=colors[i], linewidth=2)

        ax1.set_title(f"{symbol} — 1 Hour Candlestick Chart", fontsize=14)
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(DateFormatter('%H:%M'))
        plt.xticks(rotation=45)

        # RSI
        ax2.plot(df['timestamp'], rsi, color='purple', label='RSI')
        ax2.axhline(70, color='red', linestyle='--', alpha=0.5)
        ax2.axhline(30, color='green', linestyle='--', alpha=0.5)
        ax2.set_ylabel('RSI')
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='upper left')

        # MACD
        ax3.plot(df['timestamp'], macd_line, label='MACD', color='blue')
        ax3.plot(df['timestamp'], signal_line, label='Signal', color='orange')
        ax3.fill_between(df['timestamp'], macd_line - signal_line, 0, color='gray', alpha=0.3)
        ax3.axhline(0, color='black', linestyle='--')
        ax3.set_ylabel('MACD')
        ax3.grid(True, alpha=0.3)
        ax3.legend(loc='upper left')

        plt.tight_layout()
        filepath = os.path.join(PLOT_DIR, f"{symbol.replace('/', '_')}_1h.png")
        plt.savefig(filepath, dpi=100, bbox_inches='tight')
        plt.close()

        logger.info(f"1h candlestick chart saved: {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"Error plotting 1h candlestick chart for {symbol}: {e}")
        return None