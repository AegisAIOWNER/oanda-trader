import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('OANDA_API_KEY', '7bc23a1400c8e3f4095c94f9b2108772-6b53a70aba705e031e814485ad242296')
ACCOUNT_ID = os.getenv('OANDA_ACCOUNT_ID', '101-004-31357839-001')
ENVIRONMENT = os.getenv('OANDA_ENVIRONMENT', 'practice')  # 'practice' or 'live'

# Scalability configs
INSTRUMENTS = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'USD_CAD', 'AUD_USD', 'NZD_USD', 'EUR_GBP', 'USD_CHF']  # Expanded list for dynamic scanning
RATE_LIMIT_DELAY = 1.0 / 30  # 30 req/sec for practice
MARGIN_BUFFER = 0.0  # Use all available margin for single-trade strategy to maximize position size
DEFAULT_UNITS = 5000  # Increased to force bigger base sizes for viable positions
STRATEGY = 'advanced_scalp'  # New advanced scalping strategy

# For scalping
GRANULARITY = 'M5'  # 5-minute candles for scalping
CHECK_INTERVAL = 120  # 2 minutes between checks (faster signal detection)

# Risk management
STOP_LOSS_PIPS = 5  # Tighter stops for scalping (will be overridden by ATR-based stops)
TAKE_PROFIT_PIPS = 10  # Smaller targets (will be overridden by ATR-based targets)
MAX_DAILY_LOSS_PERCENT = 6.0  # Daily stop

# Advanced scalping settings
MAX_PAIRS_TO_SCAN = 25  # Maximum number of pairs to scan for signals
CONFIDENCE_THRESHOLD = 0.6  # Minimum confidence score to place a trade (0.0 to 1.0) - lowered for more trades
ATR_PERIOD = 14  # Period for ATR calculation
ATR_STOP_MULTIPLIER = 0.5  # Tighter SL to reduce stop loss hits
ATR_PROFIT_MULTIPLIER = 1.5  # Multiplier for ATR-based take profit
VOLUME_MA_PERIOD = 20  # Period for volume moving average
MIN_VOLUME_RATIO = 1.2  # Minimum volume ratio for confirmation (current volume / avg volume)

# Machine Learning settings
ENABLE_ML = True  # Enable ML predictions for enhanced decision making
ML_MODEL_PATH = 'models/rf_model.pkl'  # Path to store ML model
ML_MIN_TRAINING_SAMPLES = 5  # Minimum samples required for training (reduced for faster integration)
ML_AUTO_TRAIN_INTERVAL = 10  # Automatically retrain model after N new trades

# Position Sizing settings
POSITION_SIZING_METHOD = 'fixed_percentage'  # 'fixed_percentage' or 'kelly_criterion'
RISK_PER_TRADE = 0.02  # 2% risk per trade for fixed percentage method
KELLY_FRACTION = 0.25  # Use 25% of Kelly Criterion (quarter Kelly for safety)
MIN_TRADE_VALUE = 1.50  # Minimum trade value in account currency ($1-2 range, using $1.50 as midpoint) to meet Oanda margin requirements

# Multi-timeframe settings
ENABLE_MULTIFRAME = True  # Enable multi-timeframe confirmation
PRIMARY_TIMEFRAME = 'M5'  # Primary timeframe for signals
CONFIRMATION_TIMEFRAME = 'H1'  # Higher timeframe for confirmation

# Adaptive Threshold settings (autonomous self-optimization)
ENABLE_ADAPTIVE_THRESHOLD = True  # Enable dynamic threshold adjustment
ADAPTIVE_MIN_THRESHOLD = 0.5  # Minimum allowed threshold (safety floor)
ADAPTIVE_MAX_THRESHOLD = 0.95  # Maximum allowed threshold (safety ceiling)
ADAPTIVE_NO_SIGNAL_CYCLES = 5  # Cycles without signals before lowering threshold
ADAPTIVE_ADJUSTMENT_STEP = 0.02  # Threshold adjustment step size (2%)
ADAPTIVE_MIN_TRADES_FOR_ADJUSTMENT = 5  # Minimum trades before performance-based adjustments

# Volatility Detection settings (adaptive strategy adjustments)
ENABLE_VOLATILITY_DETECTION = True  # Enable market volatility detection
VOLATILITY_LOW_THRESHOLD = 0.0005  # ATR threshold for low volatility (e.g., 5 pips for most pairs)
VOLATILITY_NORMAL_THRESHOLD = 0.0015  # ATR threshold for normal/high volatility (e.g., 15 pips)
VOLATILITY_ADJUSTMENT_MODE = 'aggressive_threshold'  # How to adjust: 'aggressive_threshold', 'widen_stops', 'skip_cycles', 'adaptive' (all)
VOLATILITY_ATR_WINDOW = 10  # Number of cycles to average ATR for volatility detection

# Dynamic Instrument Selection settings
ENABLE_DYNAMIC_INSTRUMENTS = True  # Enable dynamic instrument selection from all available instruments
DYNAMIC_INSTRUMENT_CACHE_HOURS = 24  # Hours to cache instrument list before refreshing

# Affordability Pre-filter settings
ENABLE_AFFORDABILITY_FILTER = True  # Enable affordability check to skip instruments with insufficient margin

# Auto-scaling Position Sizing settings
ENABLE_AUTO_SCALE_UNITS = True  # Enable auto-scaling position sizing to fit available margin and risk
AUTO_SCALE_MARGIN_BUFFER = MARGIN_BUFFER  # Margin buffer for auto-scaling (reuse existing buffer by default)
AUTO_SCALE_MIN_UNITS = None  # Optional global minimum units; if None, use instrument minimumTradeSize

# Enhanced Risk Management settings (future-proofing)
MAX_OPEN_POSITIONS = 1  # Maximum concurrent open positions (single-trade strategy)
MAX_RISK_PER_TRADE = 0.5  # Maximum risk per trade (50% of balance) - increased for focused single-trade strategy on high-confidence signals like USB05Y_USD
MAX_TOTAL_RISK = 0.15  # Maximum total risk across all positions (15% of balance) - adjusted for higher individual risk
MAX_CORRELATION_POSITIONS = 2  # Maximum positions in correlated instruments (same base currency)
MAX_UNITS_PER_INSTRUMENT = 100000  # Maximum units per instrument
MAX_SLIPPAGE_PIPS = 2.0  # Maximum acceptable slippage in pips

# Input Validation settings
MIN_CANDLES_REQUIRED = 30  # Minimum candles required for strategy calculations
VALIDATE_CANDLE_DATA = True  # Enable comprehensive candle data validation
VALIDATE_ORDER_PARAMS = True  # Enable order parameter validation

# Market Hours settings
CHECK_MARKET_HOURS = True  # Check if market is open before trading
SKIP_WEEKEND_TRADING = True  # Skip trading on weekends

# Gap Detection settings
DETECT_PRICE_GAPS = True  # Detect significant price gaps
PRICE_GAP_THRESHOLD_PCT = 2.0  # Price gap threshold percentage
SKIP_TRADING_ON_GAPS = True  # Skip trading when large gaps detected

# Partial Fill Handling
PARTIAL_FILL_STRATEGY = 'ACCEPT'  # How to handle partial fills: 'ACCEPT', 'RETRY', 'CANCEL'
MIN_PARTIAL_FILL_PCT = 50  # Minimum acceptable partial fill percentage

# API Error Handling
API_RETRY_ON_DEPRECATION = True  # Retry with fallback on deprecated endpoints
API_VERSION_CHECK = True  # Check API version compatibility
MAX_API_RETRIES = 5  # Maximum retries for API calls

# Health Monitoring
ENABLE_HEALTH_CHECKS = True  # Enable health monitoring
HEALTH_CHECK_INTERVAL = 3600  # Health check interval in seconds (1 hour)
MIN_ACCOUNT_BALANCE = 10 if ENVIRONMENT == 'practice' else 100  # Minimum balance to continue trading (10 for practice, 100 for live)

# Position Monitoring (Real-time TP monitoring with trailing stops)
ENABLE_POSITION_MONITORING = True  # Enable real-time position monitoring for take profit
POSITION_MONITOR_INTERVAL = 30  # Check open positions every N seconds (default: 30)
ENABLE_TRAILING_STOPS = True  # Enable trailing stop loss mechanism
TRAILING_STOP_ATR_MULTIPLIER = 0.5  # Move SL up by 50% of ATR as profit grows
TRAILING_STOP_ACTIVATION_MULTIPLIER = 1.0  # Activate trailing after profit >= 1.0x ATR

# Logging
ENABLE_STRUCTURED_LOGGING = True  # Enable structured logging with context
LOG_LEVEL = 'INFO'  # Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL

# P&L Analytics and Reporting
ENABLE_COMPREHENSIVE_ANALYTICS = True  # Enable comprehensive P&L analytics
ANALYTICS_REPORT_INTERVAL = 3600  # Generate analytics report every N seconds (1 hour)
ANALYTICS_MIN_TRADES_FOR_SUGGESTIONS = 5  # Minimum trades before generating suggestions
ANALYTICS_DRAWDOWN_THRESHOLD = 0.10  # Alert if drawdown exceeds 10%

# Single-Trade Strategy settings
HIGH_CONFIDENCE_THRESHOLD = 0.8  # Threshold for high confidence signals
HIGH_CONFIDENCE_SL_MULTIPLIER = 1.5  # Multiplier to loosen stop loss for high confidence upward signals
ENABLE_PERSISTENT_PAIRS = True  # Enable persistent pair list across cycles
PERSISTENT_PAIRS_FILE = 'data/persistent_pairs.json'  # File to store persistent pairs
PAIR_REQUALIFICATION_INTERVAL = 300  # Seconds between pair qualification checks (5 minutes)
