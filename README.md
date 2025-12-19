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

### Try the bots for free:

- [Pumps Tracker 7%+ (Telegram)](https://t.me/+Lo7lJISTvo5iMWE6)
- [Core Pumps Tracker 4%+ (Telegram)](https://t.me/+EkA3MWC_taUxMWMy)
- [Anomaly Pumps 7%+ (Telegram)](https://t.me/+oC5lwQRniagyZWIy)

> ⚠️ Please, note, that sometimes the bots may be offline!

---

## 🎯 Three Detection Modes

This bot features **three independent detectors** that can run separately or together:

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

### ⚡ Anomaly Detector
- Detects **ultra-fast single-candle pumps** (perfect for reversal trading)
- Requires **volume spike** (5x average) + **price spike** (3x average body)
- Full reversal tracking & statistics
- Scans all exchanges
- Sends to separate Telegram channel

**Run all three simultaneously** to catch broad pumps, priority coins, and ultra-fast anomaly spikes!

---

## ✨ Features

| Feature | Main Detector | Core Detector | Anomaly Detector |
|---------|--------------|---------------|------------------|
| 🔍 **Real-time Scanning** | All available futures coins | Watchlist only | All available futures coins |
| ⚡ **Detection Criteria** | 7%+ pump, $5M+ vol | 5%+ pump, $500K+ vol | 7%+ pump + 5x volume + 3x body |
| 📊 **Technical Analysis** | RSI, Trend, ATH, Funding | RSI, Trend, ATH, Funding | RSI, Trend, ATH, Funding |
| 📈 **Multi-Exchange Data** | Binance, ByBit, BingX | Binance | Binance, ByBit, BingX |
| 🖼️ **Chart Generation** | ✅ Candlestick charts | ✅ Candlestick charts | ✅ Candlestick charts |
| 📱 **Telegram Alerts** | Main channel | Core channel | Anomaly channel |
| 📉 **Reversal Tracking** | ✅ 48h monitoring | ❌ No tracking | ✅ 48h monitoring |
| 📌 **Pinned Stats** | ✅ Auto-updating | ❌ No stats | ✅ Auto-updating |
| 🪙 **BTC Context** | ✅ Shows BTC trend | ✅ Shows BTC trend | ✅ Shows BTC trend |
| 💾 **Database** | `data/pumps.db` | `data/core.db` | `data/anomaly.db` |
| 📝 **Logs** | `pump_detector_*.log` | `core_detector_*.log` | `anomaly_detector_*.log` |

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

# Anomaly detector channel (for ultra-fast pumps)
ANOMALY_TELEGRAM_CHAT_ID=your_anomaly_channel_id_here

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
# ANOMALY DETECTOR SETTINGS (Ultra-fast pumps)
# ═══════════════════════════════════════════════════════════════
# Minimum volume spike multiplier (default: 5.0 = 5x average)
ANOMALY_MIN_VOLUME_SPIKE=5.0

# Minimum candle body multiplier (default: 3.0 = 3x average)
ANOMALY_MIN_CANDLE_BODY=3.0

# Minimum pump percentage in single candle (default: 5.0%)
ANOMALY_MIN_PUMP_PERCENT=5.0

# Hours to monitor anomaly pumps (default: 48)
MONITORING_HOURS=48

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

### Anomaly Detector Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `ANOMALY_TELEGRAM_CHAT_ID` | **required** | Anomaly channel ID (separate) |
| `ANOMALY_MIN_VOLUME_SPIKE` | `5.0` | Volume spike multiplier (5x average) |
| `ANOMALY_MIN_CANDLE_BODY` | `3.0` | Candle body spike multiplier (3x average) |
| `ANOMALY_MIN_PUMP_PERCENT` | `5.0` | Minimum pump % in single 1H candle |

### General Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `SCAN_INTERVAL_SECONDS` | `60` | Interval between market scans |
| `LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

---

## 🎯 Usage

### Running the Detectors

You have four options:

#### Option 1: Run All Detectors (Recommended)
```bash
python run_all.py
```
Runs Main, Core, and Anomaly detectors simultaneously in separate async tasks.

#### Option 2: Run Main Detector Only
```bash
python run_detector.py
# or
python run.py  # backwards compatible
```
Monitors all futures pairs with standard criteria (7%+ pump, $5M+ volume).

#### Option 3: Run Core Detector Only
```bash
python run_core.py
```
Monitors only watchlist coins with lower thresholds (5%+ pump, $500K+ volume).

#### Option 4: Run Anomaly Detector Only
```bash
python run_anomaly.py
```
Monitors all futures pairs for ultra-fast anomaly pumps (volume spike + price spike).

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

#### Anomaly Detector:
1. **Initializes** connections to all exchanges
2. **Loads** active pumps from database (survives restarts)
3. **Creates/updates** pinned statistics message
4. **Starts** scanning for volume + price spikes
5. **Tracks** reversals for 48h (same as main detector)

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

### Anomaly Detector: `data/anomaly.db`
- **pump_records** — All detected anomaly pumps with reversal data
- **pinned_messages** — Pinned message IDs for stats updates

Data persists across restarts, allowing:
- Resume monitoring active pumps (main & anomaly detectors)
- Accurate historical statistics (main & anomaly detectors)
- Per-coin performance tracking (main & anomaly detectors)

---

## 📝 Logs

Logs are stored in `logs/` with daily rotation and separated by detector:

```
logs/
├── pump_detector_2025-12-17.log      # Main detector
├── core_detector_2025-12-17.log      # Core detector
├── anomaly_detector_2025-12-17.log   # Anomaly detector
├── pump_detector_2025-12-16.log.zip  # Auto-compressed
├── core_detector_2025-12-16.log.zip
├── anomaly_detector_2025-12-16.log.zip
└── ...
```

**Log prefixes** help distinguish detectors when running all three:
- `[MAIN]` — Main detector logs
- `[CORE]` — Core detector logs
- `[ANOMALY]` — Anomaly detector logs

Example log output:
```
2025-12-17 17:23:44 | INFO | [MAIN] Scanning 825 futures pairs...
2025-12-17 17:23:44 | INFO | [CORE] Scanning 95/103 watchlist coins (on Binance)...
2025-12-17 17:23:44 | INFO | [ANOMALY] Scanning 825 futures pairs for anomalies...
2025-12-17 17:24:30 | INFO | [MAIN] Found 2 potential pump(s), analyzing...
2025-12-17 17:24:32 | INFO | [ANOMALY] Spike detected: volume 6.2x, body 4.1x
2025-12-17 17:24:35 | INFO | [CORE] ✓ SOL_USDT +5.2% (via Binance, with chart)
2025-12-17 17:24:36 | INFO | [ANOMALY] ✓ F_USDT +12.8% (via Binance, with chart, new)
```

Set `LOG_LEVEL=DEBUG` for verbose output during development.

---

## 📜 License

MIT License — feel free to use, modify, and distribute.
