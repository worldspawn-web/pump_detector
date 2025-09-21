import os
import pandas as pd
from matplotlib.dates import DateFormatter, date2num, HourLocator, MinuteLocator
import matplotlib.dates as mdates
from config import PLOT_DIR
from utils import logger
import mplfinance as mpf
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap


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

def plot_1m_candlestick_chart_with_indicators(symbol: str, ohlcv_data) -> str:
    try:
        df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['dt'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['dt'] = df['dt'] + pd.Timedelta(hours=3)  # Сдвиг на +3 часа (Москва)
        df.set_index('dt', inplace=True)

        # Рассчитываем индикаторы
        df['RSI'] = calculate_rsi(df['close'])
        macd_line, signal_line = calculate_macd(df['close'])
        df['MACD'] = macd_line
        df['Signal'] = signal_line

        # Цветовая палитра
        bg_color = '#1e1e1e'  # Темный фон
        grid_color = '#333333'  # Темная сетка
        up_color = '#4CAF50'   # Зеленый для роста
        down_color = '#F44336'  # Красный для падения
        rsi_color = '#9C27B0'  # Фиолетовый для RSI
        macd_color = '#2196F3'  # Синий для MACD
        signal_color = '#FF9800'  # Оранжевый для Signal

        # Настройка стиля для mplfinance
        mpf_style = mpf.make_mpf_style(
            base_mpf_style='nightclouds',
            rc={'font.size': 8, 'font.family': 'sans-serif'},
            marketcolors=mpf.make_marketcolors(up=up_color, down=down_color, edge='inherit', wick='inherit'),
            gridcolor=grid_color,
            gridstyle='--',
            facecolor=bg_color,
            figcolor=bg_color
        )

        # Добавляем графики
        apds = [
            mpf.make_addplot(df['RSI'], panel=1, color=rsi_color, ylabel='RSI', secondary_y=False),
            mpf.make_addplot(df[['MACD']], panel=2, type='line', color=macd_color, ylabel='MACD'),
            mpf.make_addplot(df[['Signal']], panel=2, type='line', color=signal_color)
        ]

        # Построение графика
        fig, axes = mpf.plot(
            df,
            type='candle',
            style=mpf_style,
            title=f"{symbol} — 1 Minute Candlestick Chart",
            ylabel='Price',
            volume=False,
            returnfig=True,
            addplot=apds,
            figratio=(12, 8),
            figscale=1.1,
            xrotation=45
        )

        # Настройка внешнего вида
        for ax in axes:
            ax.set_facecolor(bg_color)
            ax.grid(True, color=grid_color, linestyle='--', alpha=0.5)
            ax.tick_params(axis='x', colors='white')
            ax.tick_params(axis='y', colors='white')

        # Сохранение графика
        filepath = os.path.join(PLOT_DIR, f"{symbol.replace('/', '_')}_1m.png")
        fig.savefig(filepath, dpi=100, bbox_inches='tight', facecolor=bg_color, edgecolor=bg_color)
        plt.close(fig)
        logger.info(f"1m candlestick chart saved: {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"Error plotting 1m candlestick chart for {symbol}: {e}")
        return None

def plot_1h_candlestick_chart_with_indicators(symbol: str, ohlcv_data) -> str:
    try:
        df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['dt'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['dt'] = df['dt'] + pd.Timedelta(hours=3)  # Сдвиг на +3 часа (Москва)
        df.set_index('dt', inplace=True)

        # Рассчитываем индикаторы
        df['RSI'] = calculate_rsi(df['close'])
        macd_line, signal_line = calculate_macd(df['close'])
        df['MACD'] = macd_line
        df['Signal'] = signal_line

        # Цветовая палитра
        bg_color = '#1e1e1e'  # Темный фон
        grid_color = '#333333'  # Темная сетка
        up_color = '#4CAF50'   # Зеленый для роста
        down_color = '#F44336'  # Красный для падения
        rsi_color = '#9C27B0'  # Фиолетовый для RSI
        macd_color = '#2196F3'  # Синий для MACD
        signal_color = '#FF9800'  # Оранжевый для Signal

        # Настройка стиля для mplfinance
        mpf_style = mpf.make_mpf_style(
            base_mpf_style='nightclouds',
            rc={'font.size': 8, 'font.family': 'sans-serif'},
            marketcolors=mpf.make_marketcolors(up=up_color, down=down_color, edge='inherit', wick='inherit'),
            gridcolor=grid_color,
            gridstyle='--',
            facecolor=bg_color,
            figcolor=bg_color
        )

        # Добавляем графики
        apds = [
            mpf.make_addplot(df['RSI'], panel=1, color=rsi_color, ylabel='RSI', secondary_y=False),
            mpf.make_addplot(df[['MACD']], panel=2, type='line', color=macd_color, ylabel='MACD'),
            mpf.make_addplot(df[['Signal']], panel=2, type='line', color=signal_color)
        ]

        # Построение графика
        fig, axes = mpf.plot(
            df,
            type='candle',
            style=mpf_style,
            title=f"{symbol} — 1 Hour Candlestick Chart",
            ylabel='Price',
            volume=False,
            returnfig=True,
            addplot=apds,
            figratio=(12, 8),
            figscale=1.1,
            xrotation=45
        )

        # Настройка внешнего вида
        for ax in axes:
            ax.set_facecolor(bg_color)
            ax.grid(True, color=grid_color, linestyle='--', alpha=0.5)
            ax.tick_params(axis='x', colors='white')
            ax.tick_params(axis='y', colors='white')

        # Сохранение графика
        filepath = os.path.join(PLOT_DIR, f"{symbol.replace('/', '_')}_1h.png")
        fig.savefig(filepath, dpi=100, bbox_inches='tight', facecolor=bg_color, edgecolor=bg_color)
        plt.close(fig)
        logger.info(f"1h candlestick chart saved: {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"Error plotting 1h candlestick chart for {symbol}: {e}")
        return None