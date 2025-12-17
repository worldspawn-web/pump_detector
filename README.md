<p align="center">
  <h1 align="center">Pump Detector</h1>
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

## 🎯 Two Detection Modes

This bot features **two independent detectors** that can run separately or together:

### 📡 Main Detector
- Monitors **all Binance, ByBit, BingX & MEXC futures pairs** (800+ coins)
- Higher thresholds (7%+ pump, $5M+ volume)
- Full reversal tracking & statistics
- Sends to main Telegram channel

### 🎯 Core Detector  
- Monitors **your watchlist only** (custom coin list)
- Lower thresholds (configurable, e.g., 5%+, $500K+)
- Scans only **Binance-listed coins** (better data quality)
- No reversal tracking (lightweight)
- Sends to separate Telegram channel

**Run both simultaneously** to catch broad market pumps + early moves in your priority coins!

---

## ✨ Features

| Feature | Main Detector | Core Detector |
|---------|--------------|---------------|
| 🔍 **Real-time Scanning** | All available futures coins | Watchlist only |
| 📊 **Technical Analysis** | RSI, Trend, ATH, Funding | RSI, Trend, ATH, Funding |
| 📈 **Multi-Exchange Data** | Binance, ByBit, BingX | Binance |
| 🖼️ **Chart Generation** | ✅ Candlestick charts | ✅ Candlestick charts |
| 📱 **Telegram Alerts** | Main channel | Core channel |
| 📉 **Reversal Tracking** | ✅ 48h monitoring | ❌ No tracking |
| 📌 **Pinned Stats** | ✅ Auto-updating | ❌ No stats |
| 🪙 **BTC Context** | ✅ Shows BTC trend | ✅ Shows BTC trend |
| 💾 **Database** | `data/pumps.db` | `data/core.db` |
| 📝 **Logs** | `pump_detector_*.log` | `core_detector_*.log` |

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
TELEGRAM_CHAT_ID=your_main_channel_id_here

# Core detector channel (for watchlist coins)
CORE_TELEGRAM_CHAT_ID=your_core_channel_id_here

# ═══════════════════════════════════════════════════════════════
# MAIN DETECTOR SETTINGS
# ═══════════════════════════════════════════════════════════════
# Minimum price increase to trigger alert (default: 7.0%)
PUMP_THRESHOLD_PERCENT=7.0

# Minimum 24h volume in USD to track (default: 5000000)
MIN_VOLUME_USD=5000000

# Hours to monitor each pump for reversal (default: 48)
MONITORING_HOURS=48

# Minimum previous pumps to show coin history (default: 1)
MIN_PUMPS_FOR_HISTORY=1

# ═══════════════════════════════════════════════════════════════
# CORE DETECTOR SETTINGS (Watchlist-based)
# ═══════════════════════════════════════════════════════════════
# Lower threshold for watchlist coins (default: 5.0%)
CORE_PUMP_THRESHOLD_PERCENT=5.0

# Lower volume requirement for watchlist (default: 500000)
CORE_MIN_VOLUME_USD=500000

# Path to watchlist file (default: watchlist.txt)
WATCHLIST_FILE=watchlist.txt

# ═══════════════════════════════════════════════════════════════
# GENERAL SETTINGS
# ═══════════════════════════════════════════════════════════════
# Seconds between scans (default: 60)
SCAN_INTERVAL_SECONDS=60

# Logging level
LOG_LEVEL=INFO
```

### 5. Create watchlist (for Core Detector)

Create a `watchlist.txt` file in the project root with coins to monitor:

```txt
# Add coin symbols one per line (without _USDT suffix)
BTC
ETH
SOL
DOGE
BNB
```

---

## ⚙️ Configuration Reference

### Main Detector Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | **required** | Your Telegram bot token from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | **required** | Main channel/chat ID (use [@userinfobot](https://t.me/userinfobot)) |
| `PUMP_THRESHOLD_PERCENT` | `7.0` | Minimum % price increase to trigger alert |
| `MIN_VOLUME_USD` | `5000000` | Minimum 24h volume to consider a pump ($5M) |
| `MONITORING_HOURS` | `48` | Duration to track each pump for reversal |
| `MIN_PUMPS_FOR_HISTORY` | `1` | Previous pumps needed to show coin stats |

### Core Detector Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `CORE_TELEGRAM_CHAT_ID` | **required** | Core channel ID (separate from main) |
| `CORE_PUMP_THRESHOLD_PERCENT` | `5.0` | Lower threshold for watchlist coins |
| `CORE_MIN_VOLUME_USD` | `500000` | Lower volume requirement ($500K) |
| `WATCHLIST_FILE` | `watchlist.txt` | Path to watchlist file |

### General Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `SCAN_INTERVAL_SECONDS` | `60` | Interval between market scans |
| `LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

---

## 🎯 Usage

### Running the Detectors

You have three options:

#### Option 1: Run Both Detectors (Recommended)
```bash
python run_all.py
```
Runs both Main and Core detectors simultaneously in separate async tasks.

#### Option 2: Run Main Detector Only
```bash
python run_detector.py
# or
python run.py  # backwards compatible
```
Monitors all MEXC pairs, sends to main channel.

#### Option 3: Run Core Detector Only
```bash
python run_core.py
```
Monitors only watchlist coins, sends to core channel.

### What happens on startup

#### Main Detector:
1. **Initializes** connections to Binance, ByBit, BingX & MEXC
2. **Loads** symbol lists from all exchanges
3. **Restores** monitoring state from database (survives restarts)
4. **Creates/updates** pinned statistics message in Telegram
5. **Starts** scanning all existing futures pairs

#### Core Detector:
1. **Loads** watchlist from `watchlist.txt`
2. **Initializes** exchange connections
3. **Filters** to Binance-listed coins only
4. **Starts** scanning watchlist coins
5. **Reloads** watchlist every 10 scans (~10 minutes)

---

## 🔄 How It Works

### Main Detector Flow

```
┌─────────────────────────────────────────────────────────────┐
│                 MAIN SCAN CYCLE (60s)                       │
├─────────────────────────────────────────────────────────────┤
│  1. Fetch all MEXC futures tickers (~800 pairs)             │
│                         ↓                                   │
│  2. Filter: price change ≥ 7% AND volume ≥ $5M              │
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
│  4. Send Telegram alert to MAIN channel                     │
│                         ↓                                   │
│  5. Record pump in database for tracking                    │
│                         ↓                                   │
│  6. Update tracked pumps (check for reversals)              │
│                         ↓                                   │
│  7. Update pinned stats message (hourly)                    │
└─────────────────────────────────────────────────────────────┘
```

### Core Detector Flow

```
┌─────────────────────────────────────────────────────────────┐
│                 CORE SCAN CYCLE (60s)                       │
├─────────────────────────────────────────────────────────────┤
│  1. Load watchlist from watchlist.txt                       │
│                         ↓                                   │
│  2. Fetch MEXC tickers for watchlist coins                  │
│                         ↓                                   │
│  3. Filter to Binance-listed coins only                     │
│                         ↓                                   │
│  4. Filter: price change ≥ 5% AND volume ≥ $500K            │
│                         ↓                                   │
│  5. For each pump:                                          │
│     ├─ Fetch klines from Binance                            │
│     ├─ Calculate RSI (1M, 1H)                               │
│     ├─ Determine trend (1D, 1W)                             │
│     ├─ Fetch BTC trend for context                          │
│     ├─ Get funding rate                                     │
│     ├─ Check if ATH                                         │
│     └─ Generate candlestick chart                           │
│                         ↓                                   │
│  6. Send Telegram alert to CORE channel                     │
│                         ↓                                   │
│  7. Record in core database                                 │
│                         ↓                                   │
│  8. Reload watchlist every 10 cycles                        │
└─────────────────────────────────────────────────────────────┘
```

### Reversal Tracking (Main Detector Only)

Each detected pump is monitored for **48 hours** (configurable) to track:

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

The bot uses separate SQLite databases:

### Main Detector: `data/pumps.db`
- **pump_records** — All detected pumps with timestamps, prices, reversal data
- **pinned_messages** — Pinned message IDs for stats updates

### Core Detector: `data/core.db`
- **alerted_pumps** — Simple log of watchlist pump alerts

Data persists across restarts, allowing:
- Resume monitoring active pumps (main detector)
- Accurate historical statistics (main detector)
- Per-coin performance tracking (main detector)

---

## 📝 Logs

Logs are stored in `logs/` with daily rotation and separated by detector:

```
logs/
├── pump_detector_2025-12-17.log      # Main detector
├── core_detector_2025-12-17.log      # Core detector
├── pump_detector_2025-12-16.log.zip  # Auto-compressed
├── core_detector_2025-12-16.log.zip
└── ...
```

**Log prefixes** help distinguish detectors when running both:
- `[MAIN]` — Main detector logs
- `[CORE]` — Core detector logs

Example log output:
```
2025-12-17 17:23:44 | INFO | [MAIN] Scanning 825 futures pairs...
2025-12-17 17:23:44 | INFO | [CORE] Scanning 95/103 watchlist coins (on Binance)...
2025-12-17 17:24:30 | INFO | [MAIN] Found 2 potential pump(s), analyzing...
2025-12-17 17:24:35 | INFO | [CORE] ✓ SOL_USDT +5.2% (via Binance, with chart)
```

Set `LOG_LEVEL=DEBUG` for verbose output during development.

---

## 📜 License

MIT License — feel free to use, modify, and distribute.
