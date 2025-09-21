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

def plot_1min_chart(symbol: str, ohlcv_data) -> str:
    """1M График."""
    try:
        df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(df['timestamp'], df['close'], color='blue', linewidth=2, label='Price')
        ax.set_title(f"{symbol} — 1 Minute Chart", fontsize=14)
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(DateFormatter('%H:%M'))
        plt.xticks(rotation=45)
        plt.tight_layout()

        filepath = os.path.join(PLOT_DIR, f"{symbol.replace('/', '_')}_1m.png")
        plt.savefig(filepath, dpi=100, bbox_inches='tight')
        plt.close()

        logger.info(f"1m chart saved: {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"Error plotting 1m chart for {symbol}: {e}")
        return None

def plot_1h_chart_with_indicators(symbol: str, ohlcv_data) -> str:
    """1H график с RSI и MACD."""
    try:
        df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['rsi'] = calculate_rsi(df['close'])
        df['macd'], df['signal'] = calculate_macd(df['close'])

        # Определяем минимум и максимум для фибо
        recent_low = df['low'].min()
        recent_high = df['high'].max()

        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10), height_ratios=[3, 1, 1])

        # Цена + Фибо
        ax1.plot(df['timestamp'], df['close'], label='Price', color='blue')
        add_fibonacci_levels(ax1, recent_low, recent_high)
        ax1.set_title(f"{symbol} — 1 Hour Chart (RSI: {df['rsi'].iloc[-1]:.1f})", fontsize=12)
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper left')

        # RSI
        ax2.plot(df['timestamp'], df['rsi'], color='purple', label='RSI')
        ax2.axhline(70, color='red', linestyle='--', alpha=0.5)
        ax2.axhline(30, color='green', linestyle='--', alpha=0.5)
        ax2.set_ylabel('RSI')
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='upper left')

        # MACD
        ax3.plot(df['timestamp'], df['macd'], label='MACD', color='blue')
        ax3.plot(df['timestamp'], df['signal'], label='Signal', color='orange')
        ax3.fill_between(df['timestamp'], df['macd'] - df['signal'], 0, color='gray', alpha=0.3)
        ax3.axhline(0, color='black', linestyle='--')
        ax3.set_ylabel('MACD')
        ax3.grid(True, alpha=0.3)
        ax3.legend(loc='upper left')

        plt.tight_layout()
        filepath = os.path.join(PLOT_DIR, f"{symbol.replace('/', '_')}_1h.png")
        plt.savefig(filepath, dpi=100, bbox_inches='tight')
        plt.close()

        logger.info(f"1h chart saved: {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"Error plotting 1h chart for {symbol}: {e}")
        return None