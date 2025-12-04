<p align="center">
  <h1 align="center">🚀 MEXC Pump Detector</h1>
  <p align="center">
    <strong>Real-time cryptocurrency pump detection bot with technical analysis & Telegram alerts</strong>
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python 3.11+">
    <img src="https://img.shields.io/badge/async-httpx-green.svg" alt="Async HTTPX">
    <img src="https://img.shields.io/badge/telegram-bot-blue.svg" alt="Telegram Bot">
    <img src="https://img.shields.io/badge/license-MIT-orange.svg" alt="MIT License">
  </p>
</p>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔍 **Real-time Scanning** | Monitors all MEXC futures pairs every 60 seconds |
| 📊 **Technical Analysis** | RSI, Trend detection, ATH analysis, Funding rates |
| 📈 **Multi-Exchange Data** | Fetches TA from Binance, ByBit, BingX for accuracy |
| 🖼️ **Chart Generation** | Candlestick charts with RSI, MACD, volume & support/resistance |
| 📱 **Telegram Alerts** | Instant notifications with full analysis & trading links |
| 📉 **Reversal Tracking** | Monitors pump outcomes & calculates success statistics |
| 🪙 **BTC Context** | Shows Bitcoin trend alongside coin analysis |
| 📌 **Pinned Stats** | Auto-updating global statistics in Telegram channel |

---

## 📸 Signal Format

```
🚀 COIN_USDT 🚀

Change: +12.45%
Price: $0.004523
Volume 24h: $2,345,678

━━━ Technical Analysis ━━━

RSI: 🟠 1M: 72 | 🔴 1H: 85
Trend: 🟢 1D | 🟢 1W
BTC: 🟢 1D | 🟡 1W
Funding: +0.0150% ⚠️
ATH: ✅ $0.005200 (15.0% below)

━━━ Coin History (5 pumps) ━━━

📊 50% Retrace: 60% success | Avg: 2.5h
🎯 Full Reversal: 40% success | Avg: 5.2h
📈 Last 5: ✅❌✅✅❌ ⚡⚡⚡

Time: 14:32:15 (UTC+3)

MEXC | Binance | ByBit
```

Each signal includes a **candlestick chart** with:
- Japanese candlesticks (1H timeframe)
- Volume bars
- RSI indicator
- MACD indicator
- Support & resistance levels

---

## 🚀 Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/mexc_pump_detector.git
cd mexc_pump_detector
```

### 2. Create virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create `.env` file

Create a `.env` file in the project root with your configuration:

```env
# ═══════════════════════════════════════════════════════════════
# TELEGRAM CONFIGURATION (Required)
# ═══════════════════════════════════════════════════════════════
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_channel_id_here

# ═══════════════════════════════════════════════════════════════
# PUMP DETECTION SETTINGS
# ═══════════════════════════════════════════════════════════════
# Minimum price increase to trigger alert (default: 7.0%)
PUMP_THRESHOLD_PERCENT=7.0

# Seconds between scans (default: 60)
SCAN_INTERVAL_SECONDS=60

# Minimum 24h volume in USD to track (default: 1000000)
MIN_VOLUME_USD=1000000

# ═══════════════════════════════════════════════════════════════
# PUMP TRACKING & STATISTICS
# ═══════════════════════════════════════════════════════════════
# Hours to monitor each pump for reversal (default: 12)
MONITORING_HOURS=12

# Minimum previous pumps to show coin history (default: 1)
MIN_PUMPS_FOR_HISTORY=1

# ═══════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════
LOG_LEVEL=INFO
```

---

## ⚙️ Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | **required** | Your Telegram bot token from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | **required** | Target channel/chat ID (use [@userinfobot](https://t.me/userinfobot)) |
| `PUMP_THRESHOLD_PERCENT` | `7.0` | Minimum % price increase to trigger alert |
| `SCAN_INTERVAL_SECONDS` | `60` | Interval between market scans |
| `MIN_VOLUME_USD` | `1000000` | Minimum 24h volume to consider a pump |
| `MONITORING_HOURS` | `12` | Duration to track each pump for reversal |
| `MIN_PUMPS_FOR_HISTORY` | `1` | Previous pumps needed to show coin stats |
| `LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

---

## 🎯 Usage

### Run the pump detector

```bash
python run.py
```

Or directly:

```bash
python -m src.main
```

### What happens on startup

1. **Initializes** connections to MEXC, Binance, ByBit, BingX
2. **Loads** symbol lists from all exchanges
3. **Restores** monitoring state from database (survives restarts)
4. **Creates/updates** pinned statistics message in Telegram
5. **Starts** scanning loop

---

## 🔄 How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                      SCAN CYCLE (60s)                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Fetch all MEXC futures tickers                          │
│                         ↓                                   │
│  2. Filter: price change ≥ 7% AND volume ≥ $1M              │
│                         ↓                                   │
│  3. For each pump candidate:                                │
│     ├─ Fetch klines from Binance/ByBit/BingX               │
│     ├─ Calculate RSI (1M, 1H)                               │
│     ├─ Determine trend (1D, 1W)                             │
│     ├─ Fetch BTC trend for context                          │
│     ├─ Get funding rate                                     │
│     ├─ Check if ATH                                         │
│     ├─ Generate candlestick chart                           │
│     └─ Load coin history stats                              │
│                         ↓                                   │
│  4. Send Telegram alert with chart                          │
│                         ↓                                   │
│  5. Record pump in database for tracking                    │
│                         ↓                                   │
│  6. Update tracked pumps (check for reversals)              │
│                         ↓                                   │
│  7. Update pinned stats message (hourly)                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Reversal Tracking

Each detected pump is monitored for **12 hours** (configurable) to track:

- ⏱️ **Time to 50% retrace** — How long until price retraces 50% of the pump
- 🎯 **Full reversal** — Whether price returns to pre-pump level
- 📉 **Max drop** — Lowest point reached after the pump

Statistics are aggregated per coin and globally, displayed in:
- Individual signals (coin history)
- Pinned channel message (global stats)

---

## 📊 Technical Indicators

| Indicator | Description | Emoji Legend |
|-----------|-------------|--------------|
| **RSI** | Relative Strength Index | 🟢 < 30 (oversold) · 🟡 30-70 · 🟠 70-80 · 🔴 > 80 (overbought) |
| **Trend** | SMA-based direction | 🟢 Uptrend · 🟡 Neutral · 🔴 Downtrend |
| **Funding** | Perpetual funding rate | ✅ Normal · ⚠️ ≥ 0.5% · ❗ ≥ 1.0% |
| **ATH** | All-time high check | ❌ At ATH · ✅ Below ATH (with %) |

---

## 🗄️ Database

The bot uses SQLite (`data/pumps.db`) to store:

- **pump_records** — All detected pumps with timestamps, prices, reversal data
- **metadata** — Pinned message ID, last stats update time

Data persists across restarts, allowing:
- Resume monitoring active pumps
- Accurate historical statistics
- Per-coin performance tracking

---

## 📝 Logs

Logs are stored in `logs/` with daily rotation:

```
logs/
├── pump_detector_2025-12-04.log
├── pump_detector_2025-12-03.log.zip  # Auto-compressed
└── ...
```

Set `LOG_LEVEL=DEBUG` for verbose output during development.

---

## 🔧 Development

### Adding new features

| Component | Location | Purpose |
|-----------|----------|---------|
| Detection logic | `src/services/detector.py` | Pump criteria, analysis |
| New exchange | `src/services/` | Add new API client |
| Chart styling | `src/services/chart.py` | Visual customization |
| Message format | `src/models/signal.py` | Telegram message layout |
| Statistics | `src/services/stats.py` | Stats calculations |

### Code style

- Python 3.11+ with type hints
- Async/await patterns throughout
- PEP 8 compliant
- Dataclasses for models

---

## 📜 License

MIT License — feel free to use, modify, and distribute.
