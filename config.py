import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('OANDA_API_KEY', '7bc23a1400c8e3f4095c94f9b2108772-6b53a70aba705e031e814485ad242296')
ACCOUNT_ID = os.getenv('OANDA_ACCOUNT_ID', '101-004-31357839-001')
ENVIRONMENT = os.getenv('OANDA_ENVIRONMENT', 'practice')  # 'practice' or 'live'

# Scalability configs
INSTRUMENTS = ['EUR_USD', 'GBP_USD', 'USD_JPY']  # Add more as needed
RATE_LIMIT_DELAY = 1.0 / 30  # 30 req/sec for practice
MARGIN_BUFFER = 0.1  # 10% margin buffer
DEFAULT_UNITS = 1000  # Base trade size; reduce for scalping (e.g., 100)
STRATEGY = 'scalping_rsi'  # Changed to scalping

# For scalping
GRANULARITY = 'M5'  # 5-minute candles for scalping
CHECK_INTERVAL = 300  # 5 minutes between checks

# Risk management
STOP_LOSS_PIPS = 5  # Tighter stops for scalping
TAKE_PROFIT_PIPS = 10  # Smaller targets
MAX_DAILY_LOSS_PERCENT = 6.0  # Daily stop