# Oanda Trading Bot

A scalable, intelligent auto trading bot for Oanda with advanced scalping strategies.

## Setup

1. Create venv: `python -m venv venv`
2. Activate: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Unix)
3. Install: `pip install -r requirements.txt`
4. Set env vars or edit config.py
5. Run: `python bot.py` or `python cli.py start`

## Features

### Core Trading Features
- **Advanced Scalping Strategy**: Combines MACD, RSI, Bollinger Bands, ATR, and volume analysis
- **Dynamic Pair Selection**: Scans multiple pairs and trades the strongest signal
- **Confidence Scoring**: 0.0-1.0 scoring system filters weak signals
- **Adaptive Risk Management**: ATR-based stop losses and take profits

### Machine Learning Integration
- **ML Predictions**: Random Forest classifier predicts signal success probability
- **Confidence Boosting**: ML predictions integrated into confidence scoring (70% strategy, 30% ML)
- **Disabled by Default**: ML is disabled until model is trained to avoid low confidence scores
- **Automatic Training**: Model trains on historical OHLCV data
- **Model Persistence**: Saves and loads trained models for continuous improvement

### Enhanced Position Sizing
- **Kelly Criterion**: Optimal position sizing based on historical performance
- **Fixed Percentage**: Conservative 1-2% risk per trade
- **Confidence Adjustment**: Position size scales with signal confidence
- **Dynamic Calculation**: Adapts to account balance and market volatility

### Multi-Timeframe Analysis
- **H1 Confirmation**: Higher timeframe (1-hour) confirms M5 signals
- **Trend Detection**: Uses multiple indicators for trend determination
- **Signal Filtering**: Rejects signals contradicting higher timeframe trend
- **Confidence Boosting**: Strong confirmations increase confidence by 15%

### Advanced Backtesting
- **Walk-Forward Testing**: Robust validation with train/test periods
- **Comprehensive Metrics**: Sharpe ratio, max drawdown, win rate, and more
- **Strategy Comparison**: Test multiple strategies side-by-side
- **Performance Analytics**: Detailed trade analysis and statistics

### Error Recovery & Reliability
- **Exponential Backoff**: Intelligent retry logic for API failures
- **Circuit Breaker**: Prevents cascading failures
- **Rate Limiting Compliance**: Respects Oanda's 30 req/sec limit
- **Graceful Degradation**: Falls back when optional features fail

### Data Persistence
- **SQLite Database**: Stores complete trade history
- **Performance Tracking**: Real-time metrics and analytics
- **Model Training Data**: Historical data for ML retraining
- **Trade Analysis**: Query and analyze past performance

### Additional Features
- **Margin Checks**: Automatic margin availability verification
- **Daily Loss Limits**: Stops trading if daily loss exceeds 6%
- **Multiple Instruments**: Supports 8+ currency pairs
- **CLI Interface**: Easy command-line control with rich options
- **Comprehensive Testing**: 17 unit tests covering core functionality

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

**Basic usage (ML disabled by default):**
```bash
python cli.py start
```

**With custom options:**
```bash
# Start with ML enabled (after training the model)
python cli.py start --enable-ml

# Start with all features enabled
python cli.py start --enable-ml --enable-multiframe --position-sizing fixed_percentage

# Use Kelly Criterion for position sizing (requires trade history)
python cli.py start --position-sizing kelly_criterion
```

**Direct Python:**
```bash
python bot.py
```

### Backtesting

**Run standard backtest:**
```bash
python cli.py backtest --instrument EUR_USD --strategy advanced_scalp --cash 10000
```

**Run walk-forward analysis:**
```bash
python cli.py walkforward --instrument EUR_USD --train-period 252 --test-period 63
```

### Machine Learning

**Important: ML is disabled by default** to prevent low confidence scores from untrained models.

**Workflow:**
1. **Run bot without ML** to collect trade data (default behavior)
2. **Train the model** once you have sufficient data (200+ samples)
3. **Enable ML** to boost confidence scores with ML predictions

**Train ML model:**
```bash
python cli.py train-ml --min-samples 200
```

**Enable ML after training:**
```bash
# Via CLI
python cli.py start --enable-ml

# Or edit config.py and set ENABLE_ML = True
```

The bot automatically collects training data as it trades. Train the model periodically for better predictions.

### Performance Statistics

**View trading stats:**
```bash
python cli.py stats --days 30
```

### Configuration

Edit `config.py` to customize:

```python
# ML Settings (disabled by default until model is trained)
ENABLE_ML = False  # Set to True after training ML model
ML_MODEL_PATH = 'models/rf_model.pkl'

# Position Sizing
POSITION_SIZING_METHOD = 'fixed_percentage'  # or 'kelly_criterion'
RISK_PER_TRADE = 0.02  # 2% per trade

# Multi-timeframe
ENABLE_MULTIFRAME = True
PRIMARY_TIMEFRAME = 'M5'
CONFIRMATION_TIMEFRAME = 'H1'

# Strategy
STRATEGY = 'advanced_scalp'
CONFIDENCE_THRESHOLD = 0.8
```

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

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Trading Bot                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Strategies │  │  ML Predictor │  │ Multi-Frame  │     │
│  │   (Advanced  │──│  (Random      │──│  Analyzer    │     │
│  │    Scalp)    │  │   Forest)     │  │  (H1 Conf.)  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│         │                  │                  │             │
│         └──────────────────┴──────────────────┘             │
│                            │                                │
│                  ┌─────────▼─────────┐                      │
│                  │  Signal Generator  │                     │
│                  │  (Confidence 0-1)  │                     │
│                  └─────────┬──────────┘                     │
│                            │                                │
│                  ┌─────────▼─────────┐                      │
│                  │  Position Sizer   │                      │
│                  │ (Kelly/Fixed %)   │                      │
│                  └─────────┬──────────┘                     │
│                            │                                │
│                  ┌─────────▼─────────┐                      │
│                  │   Order Manager   │                      │
│                  │ (with Backoff)    │                      │
│                  └─────────┬──────────┘                     │
│                            │                                │
│                  ┌─────────▼─────────┐                      │
│                  │   Oanda API       │                      │
│                  └───────────────────┘                      │
└─────────────────────────────────────────────────────────────┘
                            │
                  ┌─────────▼─────────┐
                  │  SQLite Database  │
                  │  - Trade History  │
                  │  - Market Data    │
                  │  - ML Training    │
                  └───────────────────┘
```

## Requirements

- Python 3.8+
- Oanda API account (practice or live)
- SQLite3 (included with Python)
- Dependencies listed in requirements.txt

## Testing

Run unit tests to verify functionality:

```bash
python -m unittest test_trading_bot -v
```

Test coverage includes:
- Strategy signal generation
- Position sizing calculations
- ML model training and predictions
- Multi-timeframe analysis
- Database operations
- Error recovery mechanisms
- Backtesting metrics