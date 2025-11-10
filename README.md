# Oanda Trading Bot

A scalable, intelligent auto trading bot for Oanda with advanced scalping strategies.

## Setup

1. Create venv: `python -m venv venv`
2. Activate: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Unix)
3. Install: `pip install -r requirements.txt`
4. Set env vars or edit config.py
5. Run: `python bot.py` or `python cli.py start`

## Features

- **Advanced Scalping Strategy**: Combines MACD, RSI, Bollinger Bands, ATR, and volume analysis
- **Dynamic Pair Selection**: Scans multiple pairs and trades the strongest signal
- **Confidence Scoring**: 0.0-1.0 scoring system filters weak signals
- **Adaptive Risk Management**: ATR-based stop losses and take profits
- **Rate Limiting Compliance**: Respects Oanda's 30 req/sec limit
- **Margin Checks**: Automatic margin availability verification
- **Daily Loss Limits**: Stops trading if daily loss exceeds 6%
- **Multiple Instruments**: Supports 8+ currency pairs
- **Backtesting**: Test strategies on historical data
- **CLI Interface**: Easy command-line control

## Strategies

### Advanced Scalp (Recommended)

The `advanced_scalp` strategy is a sophisticated scalping system that combines multiple technical indicators for high-probability trades on 5-minute candles.

**Indicators Used:**
- **MACD (12, 26, 9)**: Identifies momentum and trend changes
- **RSI (14)**: Detects overbought/oversold conditions
- **Bollinger Bands (20, 2)**: Measures volatility and price extremes
- **ATR (14)**: Calculates adaptive stop losses and take profits
- **Volume Analysis**: Confirms signals with volume > 1.2x average

**Signal Criteria:**
- **BUY**: RSI < 30 OR price near lower Bollinger Band + MACD bullish crossover + volume confirmation
- **SELL**: RSI > 70 OR price near upper Bollinger Band + MACD bearish crossover + volume confirmation

**Confidence Score Components:**
- Base signal strength: 0.3
- MACD crossover confirmation: 0.3
- Bollinger squeeze bonus: 0.1
- Volume confirmation: 0.2
- MACD histogram momentum: 0.1

**Minimum confidence threshold**: 0.8 (configurable in config.py)

### Legacy Strategies

- **scalping_rsi**: Simple RSI-based scalping (oversold < 30, overbought > 70)
- **ma_crossover**: Moving average crossover (5/10 period)

## Configuration

Key settings in `config.py`:

```python
STRATEGY = 'advanced_scalp'  # Strategy to use
MAX_PAIRS_TO_SCAN = 10  # Maximum pairs to scan per cycle
CONFIDENCE_THRESHOLD = 0.8  # Minimum confidence for trades
INSTRUMENTS = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'USD_CAD', 'AUD_USD', ...]

# Risk Management
ATR_STOP_MULTIPLIER = 1.5  # Stop loss = 1.5 × ATR
ATR_PROFIT_MULTIPLIER = 2.5  # Take profit = 2.5 × ATR
MAX_DAILY_LOSS_PERCENT = 6.0  # Daily loss limit
```

## Usage

### Start Trading Bot
```bash
python cli.py start
# or
python bot.py
```

### Run Backtest
```bash
python cli.py backtest --instrument EUR_USD
```

### Custom Strategy
Edit `config.py` and change `STRATEGY` to one of: `advanced_scalp`, `scalping_rsi`, `ma_crossover`

## How It Works

1. **Pair Scanning**: Bot scans configured instruments for signals
2. **Signal Evaluation**: Each pair is evaluated using the selected strategy
3. **Confidence Filtering**: Only signals above the confidence threshold are considered
4. **Best Signal Selection**: The pair with the highest confidence is selected
5. **Adaptive Risk Calculation**: ATR-based stops and targets are calculated
6. **Order Placement**: A single order is placed for the best signal
7. **Safety Checks**: Margin and daily loss limits are verified

## Security

- Do not commit credentials
- Use `.env` file for API keys
- Keep `OANDA_API_KEY` and `OANDA_ACCOUNT_ID` secret
- Use practice environment for testing

## Rate Limiting

The bot implements intelligent rate limiting:
- Maximum 30 requests per second (Oanda practice limit)
- Automatic retry on 429 errors
- Batch optimization for multiple pair scanning

## Risk Management

Built-in safety features:
- **Margin Buffer**: 10% safety margin required
- **Daily Loss Limit**: Stops at 6% daily loss
- **ATR-based Stops**: Adaptive to market volatility
- **Confidence Threshold**: Filters low-probability setups

## Requirements

- Python 3.8+
- Oanda API account (practice or live)
- Dependencies listed in requirements.txt