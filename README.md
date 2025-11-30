# MEXC Pump Detector

A fast, scalable pump screener for MEXC Futures that detects rapid price anomalies and sends alerts to Telegram.

## Features

- 🚀 **Real-time Scanning**: Continuously monitors all MEXC futures pairs
- 📊 **Pump Detection**: Identifies coins with 7%+ price increases
- 📱 **Telegram Alerts**: Instant notifications with coin name, volume, and pump percentage
- ⚡ **Async Architecture**: Built for speed with async/await patterns
- 🔧 **Configurable**: Easy customization via environment variables

## Project Structure

```
mexc_pump_detector/
├── src/
│   ├── __init__.py
│   ├── config.py           # Configuration management
│   ├── main.py             # Entry point & main loop
│   ├── models/
│   │   ├── __init__.py
│   │   └── signal.py       # Data models
│   └── services/
│       ├── __init__.py
│       ├── mexc.py         # MEXC API client
│       ├── detector.py     # Pump detection logic
│       └── telegram.py     # Telegram notifications
├── logs/                   # Auto-generated logs
├── .env                    # Environment configuration
├── requirements.txt        # Python dependencies
├── run.py                  # Runner script
└── README.md
```

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd mexc_pump_detector
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/macOS
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   
   Create a `.env` file in the project root:
   ```env
   # Telegram Bot Configuration
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   TELEGRAM_CHAT_ID=your_chat_id_here
   
   # Pump Detection Settings (optional)
   PUMP_THRESHOLD_PERCENT=7.0
   SCAN_INTERVAL_SECONDS=60
   
   # Logging (optional)
   LOG_LEVEL=INFO
   ```

## Usage

Run the pump detector:

```bash
python run.py
```

Or directly:

```bash
python -m src.main
```

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | *required* | Your Telegram bot token |
| `TELEGRAM_CHAT_ID` | *required* | Target chat/channel ID |
| `PUMP_THRESHOLD_PERCENT` | `7.0` | Minimum % increase to trigger alert |
| `SCAN_INTERVAL_SECONDS` | `60` | Seconds between scans |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

## How It Works

1. **Fetches Ticker Data**: Retrieves real-time price data for all MEXC futures pairs
2. **Analyzes Price Changes**: Checks each pair's price change percentage
3. **Detects Pumps**: Identifies pairs exceeding the threshold (default 7%)
4. **Sends Alerts**: Dispatches Telegram notifications with signal details
5. **Repeats**: Waits for the configured interval and scans again

## Alert Format

```
🚀 PUMP DETECTED 🚀

Coin: BTC_USDT
Change: +8.54%
Price: $45,234.50
Volume 24h: $1,234,567,890
Time: 14:32:15 UTC
```

## Development

### Adding New Features

The codebase is designed for easy extension:

- **New Detection Logic**: Extend `PumpDetector` in `src/services/detector.py`
- **Additional Data Sources**: Add new clients in `src/services/`
- **New Alert Channels**: Create services similar to `TelegramNotifier`
- **New Models**: Add to `src/models/`

### Code Style

This project follows PEP 8 guidelines. Use type hints for all function signatures.

## License

MIT License
