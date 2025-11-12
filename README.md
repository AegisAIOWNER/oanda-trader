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
- **Curated Instrument Filter (NEW!)**: 
  - Focuses trading on highly liquid FX majors and CHF pairs for improved profitability
  - Default curated list: EUR_USD, GBP_USD, USD_JPY, USD_CAD, AUD_USD, NZD_USD, EUR_GBP, USD_CHF
  - Tighter spreads and better signal quality on major pairs
  - **Test-Safe Design**: Preserves original instrument list when no overlap exists (e.g., synthetic test symbols)
  - Applied at scan-time only, does not affect dynamic instrument loading
  - Enable/disable with `ENABLE_CURATED_FILTER = True/False` in config
  - Customize pair list with `CURATED_INSTRUMENTS` array in config
  - Clear logging shows when filter is applied and which pairs are selected
- **Dynamic Instrument Selection**: 
  - Automatically fetches ALL tradable instruments from Oanda API (forex, commodities, indices, bonds, CFDs)
  - Randomly selects subset up to MAX_PAIRS_TO_SCAN each cycle to maximize market coverage
  - Dynamically determines pip sizes from instrument metadata (pipLocation)
  - Caches instruments for 24 hours to reduce API calls
  - Fallback to config instruments if API unavailable
  - Enable with `ENABLE_DYNAMIC_INSTRUMENTS = True` in config
- **Affordability Pre-Filter (NEW!)**: 
  - Skips instruments whose minimum required margin exceeds available margin
  - Prevents INSUFFICIENT_MARGIN errors on small balances
  - Uses instrument metadata (minimumTradeSize, marginRate) from Oanda API
  - Respects margin buffer settings to keep safety cushion
  - Enable/disable with `ENABLE_AFFORDABILITY_FILTER = True/False` in config
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
- **Minimum Position Size Enforcement**: Automatically enforces minimum trade value ($1-2) to meet broker margin requirements, overriding risk-based calculations when needed while keeping stops and limits intact
- **Auto-scaling Units to Fit Available Margin & Risk (NEW!)**: 
  - Computes maximum position size that fits both available margin (with buffer) and risk constraints
  - Respects broker minimum trade sizes and configured MIN_TRADE_VALUE
  - Skips trades when computed size is below minimums or too risky (with clear logging)
  - Significantly reduces INSUFFICIENT_MARGIN errors on small balances
  - Enable with `ENABLE_AUTO_SCALE_UNITS = True` in config
  - Configure margin buffer with `AUTO_SCALE_MARGIN_BUFFER` (defaults to MARGIN_BUFFER)
  - Set optional global minimum with `AUTO_SCALE_MIN_UNITS` (defaults to instrument minimumTradeSize)

### Multi-Timeframe Analysis
- **H1 Confirmation**: Higher timeframe (1-hour) confirms M5 signals
- **Trend Detection**: Uses multiple indicators for trend determination
- **Signal Filtering**: Rejects signals contradicting higher timeframe trend
- **Confidence Boosting**: Strong confirmations increase confidence by 15%

### Autonomous Adaptive Threshold
- **AI-Like Self-Optimization**: Dynamically adjusts confidence threshold based on performance
- **Signal Frequency Adaptation**: Lowers threshold after multiple cycles without signals
- **Performance-Based Tuning**: Adjusts based on win rate and profit factor
  - High performance (65%+ win rate, 1.5+ profit factor) → Raises threshold to be more selective
  - Poor performance (45%- win rate, 0.8- profit factor) → Raises threshold to demand higher quality
  - Marginal performance (50-55% win rate, ~1.0 profit factor) → Lowers threshold for more opportunities
- **Decision Logging**: Stores all adjustments with reasoning in database for learning
- **Automatic Persistence**: ⭐ **Threshold persists across bot restarts** - never resets to config base value
- **Safety Bounds**: Configurable min/max thresholds prevent extreme adjustments
- **Transparent Reasoning**: Every adjustment logged with clear explanation
- **📚 Documentation**: See [ADAPTIVE_THRESHOLD_PERSISTENCE.md](ADAPTIVE_THRESHOLD_PERSISTENCE.md) for complete details

### Market Volatility Detection (NEW!)
- **Automatic Volatility Monitoring**: Calculates average ATR across all scanned pairs
- **Three-State Classification**: LOW, NORMAL, or HIGH volatility detection
- **Conditional Strategy Adjustments**: Adapts trading behavior based on market conditions
  - **Aggressive Threshold Mode**: Lowers confidence threshold more aggressively in low volatility
  - **Widen Stops Mode**: Increases stop-loss and take-profit ratios (1.5x-2x) to avoid whipsaws
  - **Skip Cycles Mode**: Optionally skips trading during prolonged low volatility periods
  - **Adaptive Mode** (Recommended): Combines all adjustment methods intelligently
- **Enhanced Adaptive Threshold**: Increases adjustment speed by 2x-3x in low volatility
- **Database Tracking**: Stores all volatility readings with adjustment decisions
- **Confidence Scoring**: Consistency-based confidence in volatility state detection
- **Configurable Thresholds**: Customize low/normal volatility boundaries for your pairs

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

### Future-Proofing Capabilities (NEW!)
- **Comprehensive Input Validation**:
  - Validates candle data completeness and integrity (OHLC relationships, NaN detection)
  - Validates ATR calculations with edge case handling
  - Validates all order parameters before submission
  - Detects and handles API errors gracefully
- **Enhanced Risk Management**:
  - Tracks all open positions and total exposure
  - Enforces maximum position limits (default: 3 concurrent positions)
  - Prevents over-exposure through correlation tracking (max 2 per base currency)
  - Validates slippage within acceptable limits (max 2 pips)
  - Position size limits per instrument (max 100k units)
  - Total risk exposure limit (max 10% of balance)
- **Advanced Monitoring & Logging**:
  - Structured logging with context for better debugging
  - Performance metrics for API calls, trades, and cycles
  - Health checks every hour
  - Automatic detection of system degradation
  - Comprehensive error tracking and reporting
- **Edge Case Handling**:
  - Partial fill detection and configurable handling (accept/retry/cancel)
  - Weekend/holiday market hours checking
  - Price gap detection with configurable thresholds (default: 2%)
  - Graceful API error recovery with exponential backoff
  - Network timeout handling
  - Market closed detection to prevent failed orders

### Additional Features
- **Real-Time Position Monitoring (NEW!)**: 
  - Background thread monitors open positions every 30 seconds (configurable)
  - Automatically closes positions when take profit target is reached
  - Prevents missed profit opportunities due to cycle delays
  - No waiting for signal reversal or stop loss
  - Thread-safe implementation with graceful lifecycle management
- **Margin Checks**: Automatic margin availability verification
- **Daily Loss Limits**: Stops trading if daily loss exceeds 6%
- **Multiple Instruments**: Supports ALL tradable instruments on Oanda (100+ instruments including forex, commodities, indices, bonds, CFDs)
- **CLI Interface**: Easy command-line control with rich options
- **Comprehensive Testing**: 185 unit tests (121 original + 55 future-proofing + 15 position monitoring) covering all functionality

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

**Minimum confidence threshold**: 0.8 (configurable in config.py, or dynamically adjusted by adaptive threshold system)

### Legacy Strategies

- **scalping_rsi**: Simple RSI-based scalping (oversold < 30, overbought > 70)
- **ma_crossover**: Moving average crossover (5/10 period)

## Configuration

Key settings in `config.py`:

```python
STRATEGY = 'advanced_scalp'  # Strategy to use
MAX_PAIRS_TO_SCAN = 25  # Maximum pairs to scan per cycle
CONFIDENCE_THRESHOLD = 0.7  # Base confidence for trades (raised from 0.6 for quality)
INSTRUMENTS = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'USD_CAD', 'AUD_USD', ...]

# Curated Instrument Filter (NEW!)
CURATED_INSTRUMENTS = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'USD_CAD', 'AUD_USD', 'NZD_USD', 'EUR_GBP', 'USD_CHF']
ENABLE_CURATED_FILTER = True  # Focus on high-liquidity FX majors for profitability

# Risk Management (Updated for better risk/reward)
RISK_PER_TRADE = 0.01  # 1% risk per trade (conservative, down from 2%)
ATR_STOP_MULTIPLIER = 1.0  # Stop loss = 1.0 × ATR (balanced, up from 0.5)
ATR_PROFIT_MULTIPLIER = 2.5  # Take profit = 2.5 × ATR (improved ratio, up from 1.5)
MAX_DAILY_LOSS_PERCENT = 6.0  # Daily loss limit
MIN_TRADE_VALUE = 1.50  # Minimum trade value ($1-2 range) to meet broker margin requirements
AUTO_SCALE_MARGIN_BUFFER = 0.10  # 10% margin buffer for auto-scaling (safer than 0.0)

# Adaptive Threshold (autonomous self-optimization)
ENABLE_ADAPTIVE_THRESHOLD = True  # Enable dynamic threshold adjustment
ADAPTIVE_MIN_THRESHOLD = 0.5  # Minimum allowed threshold
ADAPTIVE_MAX_THRESHOLD = 0.95  # Maximum allowed threshold
ADAPTIVE_NO_SIGNAL_CYCLES = 5  # Cycles without signals before lowering
ADAPTIVE_ADJUSTMENT_STEP = 0.02  # Adjustment step size (2%)

# Volatility Detection (adaptive strategy adjustments)
ENABLE_VOLATILITY_DETECTION = True  # Enable market volatility detection
VOLATILITY_LOW_THRESHOLD = 0.0005  # ATR threshold for low volatility (5 pips)
VOLATILITY_NORMAL_THRESHOLD = 0.0015  # ATR threshold for normal/high volatility (15 pips)
VOLATILITY_ADJUSTMENT_MODE = 'adaptive'  # 'aggressive_threshold', 'widen_stops', 'skip_cycles', or 'adaptive' (all)
VOLATILITY_ATR_WINDOW = 10  # Number of cycles to average ATR for detection

# Dynamic Instrument Selection (NEW!)
ENABLE_DYNAMIC_INSTRUMENTS = True  # Enable dynamic instrument selection from all available instruments
DYNAMIC_INSTRUMENT_CACHE_HOURS = 24  # Hours to cache instrument list before refreshing

# Enhanced Risk Management (Future-Proofing) (NEW!)
MAX_OPEN_POSITIONS = 3  # Maximum concurrent open positions (increased from 1 for diversification)
MAX_RISK_PER_TRADE = 0.5  # Maximum risk per trade (50% of balance)
MAX_TOTAL_RISK = 0.15  # Maximum total risk across all positions (15% of balance)
MAX_CORRELATION_POSITIONS = 2  # Maximum positions in correlated instruments
MAX_UNITS_PER_INSTRUMENT = 100000  # Maximum units per instrument
MAX_SLIPPAGE_PIPS = 2.0  # Maximum acceptable slippage in pips

# Input Validation (Future-Proofing) (NEW!)
MIN_CANDLES_REQUIRED = 30  # Minimum candles required for strategy calculations
VALIDATE_CANDLE_DATA = True  # Enable comprehensive candle data validation
VALIDATE_ORDER_PARAMS = True  # Enable order parameter validation

# Market Hours (Future-Proofing) (NEW!)
CHECK_MARKET_HOURS = True  # Check if market is open before trading
SKIP_WEEKEND_TRADING = True  # Skip trading on weekends

# Gap Detection (Future-Proofing) (NEW!)
DETECT_PRICE_GAPS = True  # Detect significant price gaps
PRICE_GAP_THRESHOLD_PCT = 2.0  # Price gap threshold percentage
SKIP_TRADING_ON_GAPS = True  # Skip trading when large gaps detected

# Partial Fill Handling (Future-Proofing) (NEW!)
PARTIAL_FILL_STRATEGY = 'ACCEPT'  # How to handle partial fills: 'ACCEPT', 'RETRY', 'CANCEL'
MIN_PARTIAL_FILL_PCT = 50  # Minimum acceptable partial fill percentage

# Health Monitoring (Future-Proofing) (NEW!)
ENABLE_HEALTH_CHECKS = True  # Enable health monitoring
HEALTH_CHECK_INTERVAL = 3600  # Health check interval in seconds (1 hour)
MIN_ACCOUNT_BALANCE = 10 if ENVIRONMENT == 'practice' else 100  # Minimum balance to continue trading (10 for practice, 100 for live)

# Position Monitoring (Real-time TP monitoring) (NEW!)
ENABLE_POSITION_MONITORING = True  # Enable real-time position monitoring for take profit
POSITION_MONITOR_INTERVAL = 30  # Check open positions every N seconds (default: 30)

# Logging (Future-Proofing) (NEW!)
ENABLE_STRUCTURED_LOGGING = True  # Enable structured logging with context
LOG_LEVEL = 'INFO'  # Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL
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

# Start with all features enabled (recommended)
python cli.py start --enable-ml --enable-multiframe --enable-adaptive-threshold --enable-volatility-detection

# Disable volatility detection if you prefer fixed behavior
python cli.py start --no-volatility-detection

# Use Kelly Criterion for position sizing (requires trade history)
python cli.py start --position-sizing kelly_criterion

# Disable adaptive threshold for fixed threshold behavior
python cli.py start --no-adaptive-threshold
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
MIN_TRADE_VALUE = 1.50  # Minimum trade value ($1-2 range) to meet broker margin requirements

# Multi-timeframe
ENABLE_MULTIFRAME = True
PRIMARY_TIMEFRAME = 'M5'
CONFIRMATION_TIMEFRAME = 'H1'

# Adaptive Threshold
ENABLE_ADAPTIVE_THRESHOLD = True
ADAPTIVE_MIN_THRESHOLD = 0.5
ADAPTIVE_MAX_THRESHOLD = 0.95
ADAPTIVE_NO_SIGNAL_CYCLES = 5
ADAPTIVE_ADJUSTMENT_STEP = 0.02

# Volatility Detection
ENABLE_VOLATILITY_DETECTION = True
VOLATILITY_LOW_THRESHOLD = 0.0005
VOLATILITY_NORMAL_THRESHOLD = 0.0015
VOLATILITY_ADJUSTMENT_MODE = 'adaptive'
VOLATILITY_ATR_WINDOW = 10

# Dynamic Instrument Selection (NEW!)
ENABLE_DYNAMIC_INSTRUMENTS = True  # Enable dynamic instrument selection
DYNAMIC_INSTRUMENT_CACHE_HOURS = 24  # Cache instruments for 24 hours

# Strategy
STRATEGY = 'advanced_scalp'
CONFIDENCE_THRESHOLD = 0.8  # Base threshold (adaptive when enabled)
```

## How It Works

1. **Dynamic Instrument Loading** (if enabled): On startup, bot fetches all tradable instruments from Oanda API and caches their metadata
2. **Pair Scanning**: Bot randomly selects up to MAX_PAIRS_TO_SCAN instruments from available pool (or uses config list if dynamic mode disabled)
3. **Volatility Detection** (if enabled): Calculates average ATR across all scanned pairs to determine market volatility state
4. **Signal Evaluation**: Each pair is evaluated using the selected strategy
5. **Confidence Filtering**: Only signals above the confidence threshold are considered (threshold is dynamic if adaptive mode enabled)
6. **Best Signal Selection**: The pair with the highest confidence is selected
7. **Volatility-Adjusted Risk Calculation**: ATR-based stops and targets are calculated using dynamic pip sizes from instrument metadata, with adjustments based on volatility state:
   - **Low Volatility**: Widens stops/targets by 1.5x-2x to avoid whipsaws, lowers threshold more aggressively
   - **Normal/High Volatility**: Uses standard multipliers
8. **Order Placement**: A single order is placed for the best signal
9. **Position Monitoring** (NEW!): A background thread monitors all open positions every 30 seconds:
   - Retrieves current profit for each position in real-time
   - Calculates profit in pips based on current market price
   - Closes position immediately when profit >= ATR-based take profit target
   - Updates database with closure status
   - Ensures profits are locked in without waiting for next trading cycle
9. **Safety Checks**: Margin and daily loss limits are verified
9. **Adaptive Learning** (if enabled): 
   - Threshold automatically adjusts after each cycle based on signal frequency
   - Adjustment speed increases 2x-3x in low volatility conditions
   - Threshold adjusts after trades based on recent win rate and profit factor
   - All adjustments are logged with reasoning in the database for transparency
10. **Volatility Tracking**: All volatility readings and adjustments are stored for analysis

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
# Run main bot tests
python -m unittest test_trading_bot -v

# Run adaptive threshold tests (8 tests)
python -m unittest discover -s . -p "test_adaptive*.py" -v

# Run demonstration of threshold persistence
python demo_threshold_persistence.py
```

Test coverage includes:
- Strategy signal generation
- Position sizing calculations
- ML model training and predictions
- Multi-timeframe analysis
- Database operations
- Error recovery mechanisms
- Backtesting metrics
- **Adaptive threshold persistence** (8 comprehensive tests)
  - Lifecycle and adjustment logic
  - Persistence across restarts ⭐
  - Edge cases (bounds, empty DB, rapid adjustments)
  - See [test_adaptive_integration.py](test_adaptive_integration.py) and [test_adaptive_threshold_edge_cases.py](test_adaptive_threshold_edge_cases.py)