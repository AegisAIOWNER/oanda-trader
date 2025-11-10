import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('OANDA_API_KEY', '7bc23a1400c8e3f4095c94f9b2108772-6b53a70aba705e031e814485ad242296')
ACCOUNT_ID = os.getenv('OANDA_ACCOUNT_ID', '101-004-31357839-001')
ENVIRONMENT = os.getenv('OANDA_ENVIRONMENT', 'practice')  # 'practice' or 'live'

# Scalability configs
INSTRUMENTS = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'USD_CAD', 'AUD_USD', 'NZD_USD', 'EUR_GBP', 'USD_CHF']  # Expanded list for dynamic scanning
RATE_LIMIT_DELAY = 1.0 / 30  # 30 req/sec for practice
MARGIN_BUFFER = 0.1  # 10% margin buffer
DEFAULT_UNITS = 1000  # Base trade size; reduce for scalping (e.g., 100)
STRATEGY = 'advanced_scalp'  # New advanced scalping strategy

# For scalping
GRANULARITY = 'M5'  # 5-minute candles for scalping
CHECK_INTERVAL = 300  # 5 minutes between checks

# Risk management
STOP_LOSS_PIPS = 5  # Tighter stops for scalping (will be overridden by ATR-based stops)
TAKE_PROFIT_PIPS = 10  # Smaller targets (will be overridden by ATR-based targets)
MAX_DAILY_LOSS_PERCENT = 6.0  # Daily stop

# Advanced scalping settings
MAX_PAIRS_TO_SCAN = 10  # Maximum number of pairs to scan for signals
CONFIDENCE_THRESHOLD = 0.8  # Minimum confidence score to place a trade (0.0 to 1.0)
ATR_PERIOD = 14  # Period for ATR calculation
ATR_STOP_MULTIPLIER = 1.5  # Multiplier for ATR-based stop loss
ATR_PROFIT_MULTIPLIER = 2.5  # Multiplier for ATR-based take profit
VOLUME_MA_PERIOD = 20  # Period for volume moving average
MIN_VOLUME_RATIO = 1.2  # Minimum volume ratio for confirmation (current volume / avg volume)

# Machine Learning settings
ENABLE_ML = True  # Enable ML predictions
ML_MODEL_PATH = 'models/rf_model.pkl'  # Path to store ML model
ML_MIN_TRAINING_SAMPLES = 200  # Minimum samples required for training

# Position Sizing settings
POSITION_SIZING_METHOD = 'fixed_percentage'  # 'fixed_percentage' or 'kelly_criterion'
RISK_PER_TRADE = 0.02  # 2% risk per trade for fixed percentage method
KELLY_FRACTION = 0.25  # Use 25% of Kelly Criterion (quarter Kelly for safety)

# Multi-timeframe settings
ENABLE_MULTIFRAME = True  # Enable multi-timeframe confirmation
PRIMARY_TIMEFRAME = 'M5'  # Primary timeframe for signals
CONFIRMATION_TIMEFRAME = 'H1'  # Higher timeframe for confirmation