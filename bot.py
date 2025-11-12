print("DEBUG: Starting bot.py - before imports", flush=True)
import oandapyV20
import oandapyV20.endpoints.accounts as accounts
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.instruments as instruments
import oandapyV20.endpoints.positions as positions
import pandas as pd
import time
import logging
import random
import threading
from datetime import datetime, timedelta
from config import *
from strategies import get_signal, get_signal_with_confidence
from database import TradeDatabase
from ml_predictor import MLPredictor
from position_sizing import PositionSizer
from multi_timeframe import MultiTimeframeAnalyzer
from error_recovery import ExponentialBackoff, api_circuit_breaker
from adaptive_threshold import AdaptiveThresholdManager
from volatility_detector import VolatilityDetector
from validation import DataValidator, RiskValidator
from risk_manager import RiskManager, OrderResponseHandler
from monitoring import StructuredLogger, PerformanceMonitor, HealthChecker
from trailing_stops import TrailingStopManager
from analytics import AnalyticsEngine
from persistent_pairs import PersistentPairsManager
print("DEBUG: All imports completed successfully", flush=True)

class OandaTradingBot:
    def __init__(self, enable_ml=True, enable_multiframe=True, position_sizing_method='fixed_percentage',
                 enable_adaptive_threshold=True, enable_volatility_detection=True):
        print("DEBUG: Entering OandaTradingBot.__init__", flush=True)
        print(f"DEBUG: Parameters - ML: {enable_ml}, Multiframe: {enable_multiframe}, "
              f"Position sizing: {position_sizing_method}, Adaptive threshold: {enable_adaptive_threshold}, "
              f"Volatility detection: {enable_volatility_detection}", flush=True)
        self.api = oandapyV20.API(access_token=API_KEY, environment=ENVIRONMENT)
        self.account_id = ACCOUNT_ID
        self.last_request_time = time.time()
        self.daily_pnl = 0.0
        print("DEBUG: Basic attributes initialized", flush=True)
        
        # Exponential backoff for API calls (initialize before any API calls)
        self.api_backoff = ExponentialBackoff(base_delay=1.0, max_delay=30.0, max_retries=5)
        print("DEBUG: Exponential backoff initialized", flush=True)
        
        # Initialize database
        print("DEBUG: Initializing database...", flush=True)
        self.db = TradeDatabase()
        print("DEBUG: Database initialized", flush=True)
        
        # Initialize ML predictor
        print(f"DEBUG: Initializing ML predictor (enabled: {enable_ml})...", flush=True)
        self.enable_ml = enable_ml
        self.ml_predictor = MLPredictor() if enable_ml else None
        print("DEBUG: ML predictor initialized", flush=True)
        
        # Initialize position sizer
        print("DEBUG: Initializing position sizer...", flush=True)
        self.position_sizer = PositionSizer(method=position_sizing_method, risk_per_trade=0.02, min_trade_value=MIN_TRADE_VALUE)
        print("DEBUG: Position sizer initialized", flush=True)
        
        # Initialize multi-timeframe analyzer
        print(f"DEBUG: Initializing multi-timeframe analyzer (enabled: {enable_multiframe})...", flush=True)
        self.enable_multiframe = enable_multiframe
        self.mtf_analyzer = MultiTimeframeAnalyzer(primary_timeframe='M5', 
                                                    confirmation_timeframe='H1') if enable_multiframe else None
        print("DEBUG: Multi-timeframe analyzer initialized", flush=True)
        
        # Initialize volatility detector
        print(f"DEBUG: Initializing volatility detector (enabled: {enable_volatility_detection})...", flush=True)
        self.enable_volatility_detection = enable_volatility_detection
        self.volatility_detector = VolatilityDetector(
            low_threshold=VOLATILITY_LOW_THRESHOLD,
            normal_threshold=VOLATILITY_NORMAL_THRESHOLD,
            adjustment_mode=VOLATILITY_ADJUSTMENT_MODE,
            atr_window=VOLATILITY_ATR_WINDOW
        ) if enable_volatility_detection else None
        print("DEBUG: Volatility detector initialized", flush=True)
        
        # Initialize adaptive threshold manager (with volatility detector if enabled)
        print(f"DEBUG: Initializing adaptive threshold manager (enabled: {enable_adaptive_threshold})...", flush=True)
        self.enable_adaptive_threshold = enable_adaptive_threshold
        self.adaptive_threshold_mgr = AdaptiveThresholdManager(
            base_threshold=CONFIDENCE_THRESHOLD,
            db=self.db,
            min_threshold=ADAPTIVE_MIN_THRESHOLD,
            max_threshold=ADAPTIVE_MAX_THRESHOLD,
            no_signal_cycles_trigger=ADAPTIVE_NO_SIGNAL_CYCLES,
            adjustment_step=ADAPTIVE_ADJUSTMENT_STEP,
            volatility_detector=self.volatility_detector
        ) if enable_adaptive_threshold else None
        print("DEBUG: Adaptive threshold manager initialized", flush=True)
        
        # Initialize dynamic instruments if enabled
        print(f"DEBUG: Initializing dynamic instruments (enabled: {ENABLE_DYNAMIC_INSTRUMENTS})...", flush=True)
        self.enable_dynamic_instruments = ENABLE_DYNAMIC_INSTRUMENTS
        self.instruments_cache = {}  # Cache of {instrument_name: {pipLocation, displayName, type, etc.}}
        self.instruments_cache_time = None  # Time when cache was last updated
        
        if self.enable_dynamic_instruments:
            print("DEBUG: Fetching dynamic instruments from API...", flush=True)
            self._fetch_and_cache_instruments()
            print(f"DEBUG: Cached {len(self.instruments_cache)} instruments", flush=True)
        
        # Initialize validation and risk management (future-proofing)
        print("DEBUG: Initializing validation and risk management...", flush=True)
        self.data_validator = DataValidator()
        self.risk_validator = RiskValidator(
            max_open_positions=MAX_OPEN_POSITIONS,
            max_risk_per_trade=MAX_RISK_PER_TRADE,
            max_total_risk=MAX_TOTAL_RISK,
            max_slippage_pips=MAX_SLIPPAGE_PIPS
        )
        self.risk_manager = RiskManager(
            max_open_positions=MAX_OPEN_POSITIONS,
            max_risk_per_trade=MAX_RISK_PER_TRADE,
            max_total_risk=MAX_TOTAL_RISK,
            max_correlation_positions=MAX_CORRELATION_POSITIONS,
            max_units_per_instrument=MAX_UNITS_PER_INSTRUMENT
        )
        self.order_response_handler = OrderResponseHandler()
        print("DEBUG: Validation and risk management initialized", flush=True)
        
        # Initialize monitoring and logging
        print("DEBUG: Initializing monitoring and logging...", flush=True)
        log_level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        self.structured_logger = StructuredLogger(
            name='TradingBot',
            log_level=log_level_map.get(LOG_LEVEL, logging.INFO)
        ) if ENABLE_STRUCTURED_LOGGING else None
        self.performance_monitor = PerformanceMonitor() if ENABLE_HEALTH_CHECKS else None
        self.last_health_check = None
        print("DEBUG: Monitoring and logging initialized", flush=True)
        
        # Initialize trailing stop manager
        print("DEBUG: Initializing trailing stop manager...", flush=True)
        self.enable_trailing_stops = ENABLE_TRAILING_STOPS
        self.trailing_stop_manager = TrailingStopManager(
            atr_multiplier=TRAILING_STOP_ATR_MULTIPLIER,
            activation_multiplier=TRAILING_STOP_ACTIVATION_MULTIPLIER
        ) if ENABLE_TRAILING_STOPS else None
        print("DEBUG: Trailing stop manager initialized", flush=True)
        
        # Initialize analytics engine
        print("DEBUG: Initializing analytics engine...", flush=True)
        self.enable_comprehensive_analytics = ENABLE_COMPREHENSIVE_ANALYTICS
        self.analytics_engine = AnalyticsEngine(
            db=self.db,
            min_trades_for_suggestions=ANALYTICS_MIN_TRADES_FOR_SUGGESTIONS,
            drawdown_threshold=ANALYTICS_DRAWDOWN_THRESHOLD
        ) if ENABLE_COMPREHENSIVE_ANALYTICS else None
        self.analytics_report_interval = ANALYTICS_REPORT_INTERVAL
        self.last_analytics_report = None
        print("DEBUG: Analytics engine initialized", flush=True)
        
        # Initialize position monitoring thread
        print("DEBUG: Initializing position monitoring...", flush=True)
        self.enable_position_monitoring = ENABLE_POSITION_MONITORING
        self.position_monitor_interval = POSITION_MONITOR_INTERVAL
        self.position_monitor_thread = None
        self.position_monitor_stop_event = threading.Event()
        print("DEBUG: Position monitoring initialized", flush=True)
        
        # ML auto-training tracking
        self.ml_auto_train_interval = ML_AUTO_TRAIN_INTERVAL if hasattr(self, 'enable_ml') and self.enable_ml else None
        self.ml_trades_since_last_train = 0
        
        # Initialize persistent pairs manager for single-trade strategy
        print("DEBUG: Initializing persistent pairs manager...", flush=True)
        self.enable_persistent_pairs = ENABLE_PERSISTENT_PAIRS
        self.persistent_pairs_mgr = PersistentPairsManager(
            storage_file=PERSISTENT_PAIRS_FILE,
            requalification_interval=PAIR_REQUALIFICATION_INTERVAL,
            max_pairs=MAX_PAIRS_TO_SCAN
        ) if ENABLE_PERSISTENT_PAIRS else None
        print("DEBUG: Persistent pairs manager initialized", flush=True)
        
        # Initialize daily start balance after all components are ready
        print("DEBUG: Attempting to get balance...", flush=True)
        self.daily_start_balance = self.get_balance()
        print(f"DEBUG: Balance retrieved: {self.daily_start_balance}", flush=True)
        
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        logging.info(f"Bot initialized - ML: {enable_ml} (auto-train: {self.ml_auto_train_interval} trades), "
                     f"Multi-timeframe: {enable_multiframe}, "
                     f"Position sizing: {position_sizing_method}, Adaptive threshold: {enable_adaptive_threshold}, "
                     f"Volatility detection: {enable_volatility_detection} (mode: {VOLATILITY_ADJUSTMENT_MODE}), "
                     f"Dynamic instruments: {ENABLE_DYNAMIC_INSTRUMENTS}, "
                     f"Risk management: enabled (max risk/trade: {MAX_RISK_PER_TRADE:.1%}), "
                     f"Health monitoring: {ENABLE_HEALTH_CHECKS}, "
                     f"Position monitoring: {ENABLE_POSITION_MONITORING}, "
                     f"Trailing stops: {ENABLE_TRAILING_STOPS}, "
                     f"Comprehensive analytics: {ENABLE_COMPREHENSIVE_ANALYTICS}, "
                     f"Persistent pairs: {ENABLE_PERSISTENT_PAIRS}, "
                     f"Single-trade strategy: {MAX_OPEN_POSITIONS == 1}")
        print("DEBUG: OandaTradingBot.__init__ completed successfully", flush=True)

    def _rate_limited_request(self, endpoint):
        """Execute API request with rate limiting and exponential backoff."""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY - elapsed)
        self.last_request_time = current_time
        
        start_time = time.time()
        success = False
        error = None
        result = None
        
        def _execute_request():
            try:
                # Use circuit breaker to prevent cascading failures
                return api_circuit_breaker.call(self.api.request, endpoint)
            except Exception as e:
                if '429' in str(e):
                    logging.warning("Rate limit hit, will retry with backoff.")
                    raise  # Let exponential backoff handle retry
                raise
        
        try:
            # Execute with exponential backoff
            result = self.api_backoff.execute_with_retry(_execute_request)
            success = True
            
            # Validate API response
            if VALIDATE_ORDER_PARAMS and hasattr(self, 'data_validator'):
                is_valid, error_msg = self.data_validator.validate_api_response(result)
                if not is_valid:
                    logging.warning(f"API response validation warning: {error_msg}")
            
            return result
        
        except Exception as e:
            success = False
            error = e
            if hasattr(self, 'structured_logger') and self.structured_logger:
                self.structured_logger.log_api_error(str(endpoint.__class__.__name__), e)
            raise
        
        finally:
            # Record API call metrics
            duration = time.time() - start_time
            if hasattr(self, 'performance_monitor') and self.performance_monitor:
                self.performance_monitor.record_api_call(success, duration, error)

    def _fetch_and_cache_instruments(self):
        """Fetch all tradable instruments from Oanda API and cache their metadata."""
        try:
            r = accounts.AccountInstruments(accountID=self.account_id)
            response = self._rate_limited_request(r)
            
            instruments_list = response.get('instruments', [])
            self.instruments_cache = {}
            
            for inst in instruments_list:
                name = inst.get('name')
                if name:
                    # Store relevant metadata
                    self.instruments_cache[name] = {
                        'pipLocation': inst.get('pipLocation', -4),
                        'displayName': inst.get('displayName', name),
                        'type': inst.get('type', 'CURRENCY'),
                        'displayPrecision': inst.get('displayPrecision', 5),
                        'tradeUnitsPrecision': inst.get('tradeUnitsPrecision', 0),
                        'minimumTradeSize': inst.get('minimumTradeSize', '1'),
                        'maximumOrderUnits': inst.get('maximumOrderUnits', '100000000'),
                        'marginRate': inst.get('marginRate', 0.0333)
                    }
            
            self.instruments_cache_time = datetime.now()
            logging.info(f"Cached {len(self.instruments_cache)} tradable instruments from Oanda API")
            
            # Log some sample instruments for visibility
            sample_instruments = list(self.instruments_cache.keys())[:10]
            logging.info(f"Sample instruments: {', '.join(sample_instruments)}")
            
        except Exception as e:
            logging.error(f"Failed to fetch instruments from API: {e}")
            # Fall back to config instruments if dynamic fetch fails
            logging.warning("Falling back to config INSTRUMENTS list")
            for inst in INSTRUMENTS:
                self.instruments_cache[inst] = {
                    'pipLocation': -2 if 'JPY' in inst else -4,
                    'displayName': inst,
                    'type': 'CURRENCY',
                    'displayPrecision': 3 if 'JPY' in inst else 5,
                    'tradeUnitsPrecision': 0,
                    'minimumTradeSize': '1',
                    'maximumOrderUnits': '100000000',
                    'marginRate': 0.0333  # Default ~30:1 leverage
                }
            self.instruments_cache_time = datetime.now()
    
    def _should_refresh_instruments_cache(self):
        """Check if instruments cache should be refreshed."""
        if not self.instruments_cache_time:
            return True
        
        hours_since_cache = (datetime.now() - self.instruments_cache_time).total_seconds() / 3600
        return hours_since_cache >= DYNAMIC_INSTRUMENT_CACHE_HOURS
    
    def _get_instrument_pip_size(self, instrument):
        """Get pip size for an instrument from cache or fetch from API.
        
        Args:
            instrument: Instrument name (e.g., 'EUR_USD', 'USD_JPY')
            
        Returns:
            float: Pip size (e.g., 0.0001 for EUR_USD, 0.01 for USD_JPY)
        """
        # Check if instrument is in cache
        if instrument in self.instruments_cache:
            pip_location = self.instruments_cache[instrument]['pipLocation']
            return 10 ** pip_location
        
        # If not in cache, try to fetch from API
        if self.enable_dynamic_instruments:
            try:
                r = accounts.AccountInstruments(accountID=self.account_id)
                response = self._rate_limited_request(r)
                
                instruments_list = response.get('instruments', [])
                for inst in instruments_list:
                    if inst.get('name') == instrument:
                        # Cache this instrument for future use
                        self.instruments_cache[instrument] = {
                            'pipLocation': inst.get('pipLocation', -4),
                            'displayName': inst.get('displayName', instrument),
                            'type': inst.get('type', 'CURRENCY'),
                            'displayPrecision': inst.get('displayPrecision', 5),
                            'tradeUnitsPrecision': inst.get('tradeUnitsPrecision', 0),
                            'minimumTradeSize': inst.get('minimumTradeSize', '1'),
                            'maximumOrderUnits': inst.get('maximumOrderUnits', '100000000'),
                            'marginRate': inst.get('marginRate', 0.0333)
                        }
                        pip_location = inst.get('pipLocation', -4)
                        return 10 ** pip_location
                
                # If instrument not found in API response, log warning
                logging.warning(f"Instrument {instrument} not found in API response")
            except Exception as e:
                logging.error(f"Failed to fetch instrument {instrument} from API: {e}")
        
        # Final fallback to legacy logic (only when API unavailable)
        logging.warning(f"Using legacy pip size logic for {instrument}")
        if 'JPY' in instrument:
            return 0.01
        else:
            return 0.0001
    
    def _calculate_pip_value(self, instrument, price):
        """Calculate pip value (pip size) for an instrument.
        
        The pip value represents the price change per pip per unit of the instrument.
        This is equivalent to the pip size of the instrument.
        
        For position sizing calculations:
        - Risk = units * stop_loss_pips * pip_value
        - Units = risk_amount / (stop_loss_pips * pip_value)
        
        Args:
            instrument: Instrument name (e.g., 'EUR_USD', 'GBP_NZD')
            price: Current price of the instrument (for validation)
            
        Returns:
            float: Pip value per unit (e.g., 0.0001 for EUR_USD, 0.01 for USD_JPY)
        """
        if not price or price <= 0:
            logging.warning(f"Invalid price {price} for {instrument}, using pip size for calculation")
        
        # Get pip size for this instrument - this IS the pip value per unit
        pip_value = self._get_instrument_pip_size(instrument)
        
        price_str = f"{price:.5f}" if price and price > 0 else "N/A"
        logging.debug(f"Calculated pip value for {instrument}: {pip_value} (price={price_str})")
        
        return pip_value
    
    def _is_instrument_affordable(self, instrument: str, current_price: float, 
                                   available_margin: float, margin_buffer: float = MARGIN_BUFFER) -> tuple:
        """Check if an instrument is affordable based on minimum trade size and available margin.
        
        Args:
            instrument: Instrument name (e.g., 'EUR_USD', 'USD_JPY')
            current_price: Current price of the instrument
            available_margin: Available margin from account
            margin_buffer: Fraction of available margin to keep as buffer (0.0-1.0)
            
        Returns:
            tuple: (is_affordable: bool, reason: str)
        """
        # Get instrument metadata from cache
        inst_data = self.instruments_cache.get(instrument, {})
        
        # Safe type conversion for metadata values (they may be strings from API)
        try:
            min_units = float(inst_data.get('minimumTradeSize', '1'))
        except (ValueError, TypeError):
            min_units = 1.0
            logging.debug(f"Invalid minimumTradeSize for {instrument}, using 1.0")
        
        try:
            margin_rate = float(inst_data.get('marginRate', 0.0333))
        except (ValueError, TypeError):
            margin_rate = 0.0333  # Default ~30:1 leverage
            logging.debug(f"Invalid marginRate for {instrument}, using 0.0333")
        
        # Safe type conversion for input parameters
        try:
            current_price = float(current_price)
        except (ValueError, TypeError):
            current_price = 0.0
            logging.warning(f"Invalid current_price for {instrument}: {current_price}")
        
        try:
            available_margin = float(available_margin)
        except (ValueError, TypeError):
            available_margin = 0.0
            logging.warning(f"Invalid available_margin: {available_margin}")
        
        try:
            margin_buffer = float(margin_buffer)
        except (ValueError, TypeError):
            margin_buffer = 0.5
            logging.debug(f"Invalid margin_buffer, using 0.5")
        
        # Calculate required margin for minimum trade size
        # Formula: required_margin = min_units * current_price * margin_rate
        required_margin = max(0.0, min_units * current_price * margin_rate)
        
        # Calculate effective available margin after buffer
        # margin_buffer is fraction to keep as buffer (e.g., 0.5 = keep 50% as buffer)
        effective_available = max(0.0, available_margin * (1.0 - margin_buffer))
        
        # Check affordability
        is_affordable = required_margin <= effective_available
        
        reason = f"Needs {required_margin:.2f} {'<=' if is_affordable else '>'} avail {effective_available:.2f}"
        
        if not is_affordable:
            logging.debug(f"Affordability check for {instrument}: {reason} (min_units={min_units}, "
                         f"price={current_price:.5f}, margin_rate={margin_rate:.4f})")
        
        return is_affordable, reason
    
    def _get_available_instruments(self):
        """Get list of instruments to scan.
        
        Returns:
            list: List of instrument names to scan
        """
        if self.enable_dynamic_instruments:
            # Refresh cache if needed
            if self._should_refresh_instruments_cache():
                logging.info("Refreshing instruments cache...")
                self._fetch_and_cache_instruments()
            
            # Return all cached instruments
            return list(self.instruments_cache.keys())
        else:
            # Return config instruments
            return INSTRUMENTS

    def get_open_position_instruments(self):
        """Get list of instruments with currently open positions.
        
        Returns:
            list: List of instrument names that have open positions
        """
        try:
            r = positions.OpenPositions(accountID=self.account_id)
            response = self._rate_limited_request(r)
            api_positions = response.get('positions', [])
            
            open_instruments = []
            for pos in api_positions:
                instrument = pos.get('instrument')
                if not instrument:
                    continue
                
                long_units = float(pos.get('long', {}).get('units', 0))
                short_units = float(pos.get('short', {}).get('units', 0))
                
                # Calculate net position
                net_units = long_units + short_units  # short_units is negative
                
                if net_units != 0:
                    open_instruments.append(instrument)
            
            logging.debug(f"Found {len(open_instruments)} open positions: {open_instruments}")
            return open_instruments
        
        except Exception as e:
            logging.warning(f"Failed to get open positions: {e}")
            return []
    
    def get_balance(self):
        r = accounts.AccountSummary(accountID=self.account_id)
        response = self._rate_limited_request(r)
        return float(response['account']['balance'])
    
    def get_margin_info(self):
        """
        Get margin information from account.
        
        Returns:
            dict: Dictionary with 'balance', 'margin_available', 'margin_used'
        """
        r = accounts.AccountSummary(accountID=self.account_id)
        response = self._rate_limited_request(r)
        return {
            'balance': float(response['account']['balance']),
            'margin_available': float(response['account']['marginAvailable']),
            'margin_used': float(response['account'].get('marginUsed', 0))
        }

    def check_margin(self):
        r = accounts.AccountSummary(accountID=self.account_id)
        response = self._rate_limited_request(r)
        margin_available = float(response['account']['marginAvailable'])
        balance = float(response['account']['balance'])
        return margin_available > (balance * MARGIN_BUFFER)

    def get_prices(self, instrument, count=50, granularity=GRANULARITY):
        params = {'count': count, 'granularity': granularity}
        r = instruments.InstrumentsCandles(instrument=instrument, params=params)
        response = self._rate_limited_request(r)
        candles = response.get('candles', [])
        data = []
        for c in candles:
            if c['complete']:
                data.append({
                    'time': c['time'],
                    'open': float(c['mid']['o']),
                    'high': float(c['mid']['h']),
                    'low': float(c['mid']['l']),
                    'close': float(c['mid']['c']),
                    'volume': int(c['volume'])
                })
        
        df = pd.DataFrame(data)
        
        # Validate candle data if enabled
        if VALIDATE_CANDLE_DATA and not df.empty:
            is_valid, error_msg = self.data_validator.validate_candle_data(
                df, instrument, min_candles=MIN_CANDLES_REQUIRED
            )
            if not is_valid:
                logging.error(f"Candle data validation failed for {instrument}: {error_msg}")
                if self.structured_logger:
                    self.structured_logger.log_validation_error(
                        "candle_data", error_msg, instrument=instrument
                    )
                # Return empty DataFrame to signal failure
                return pd.DataFrame()
        
        return df

    def place_order(self, instrument, side, units, sl_pips=None, tp_pips=None, current_price=None):
        if not self.check_margin():
            logging.warning(f"Insufficient margin for {instrument}, skipping.")
            if self.performance_monitor:
                self.performance_monitor.record_trade_attempt(False, "Insufficient margin")
            return None
        
        # Validate order parameters
        if VALIDATE_ORDER_PARAMS:
            is_valid, error_msg = self.data_validator.validate_order_params(
                instrument, units, sl_pips, tp_pips,
                max_units=MAX_UNITS_PER_INSTRUMENT
            )
            if not is_valid:
                logging.error(f"Order validation failed for {instrument}: {error_msg}")
                if self.structured_logger:
                    self.structured_logger.log_validation_error(
                        "order_params", error_msg, instrument=instrument
                    )
                if self.performance_monitor:
                    self.performance_monitor.record_trade_attempt(False, f"Validation failed: {error_msg}")
                return None
        
        # Check market hours
        if CHECK_MARKET_HOURS and SKIP_WEEKEND_TRADING:
            is_closed, reason = self.data_validator.is_market_closed()
            if is_closed:
                logging.info(f"Market closed, skipping order for {instrument}: {reason}")
                if self.structured_logger:
                    self.structured_logger.log_trade_decision(
                        instrument, side, 0.0, "SKIPPED", reason
                    )
                return None
        
        # Check risk limits - calculate pip value based on instrument and price
        balance = self.get_balance()
        
        # Get current price if not provided
        if current_price is None:
            try:
                df = self.get_prices(instrument, count=1, granularity=GRANULARITY)
                if not df.empty:
                    current_price = df['close'].iloc[-1]
                else:
                    current_price = 1.0  # Fallback
            except Exception as e:
                logging.warning(f"Failed to get current price for {instrument}: {e}, using fallback")
                current_price = 1.0
        
        # Calculate pip value for this instrument
        pip_value = self._calculate_pip_value(instrument, current_price)
        
        # Calculate risk amount using proper pip value
        # Formula: risk = units * stop_loss_pips * pip_value_per_unit
        risk_amount = abs(units * sl_pips * pip_value) if sl_pips else 0
        
        can_open, reason = self.risk_manager.can_open_position(instrument, units, risk_amount, balance)
        if not can_open:
            logging.warning(f"Risk check failed for {instrument}: {reason}")
            if self.structured_logger:
                self.structured_logger.log_risk_check("position_limit", False, reason, instrument=instrument)
            if self.performance_monitor:
                self.performance_monitor.record_trade_attempt(False, f"Risk check failed: {reason}")
            return None
        
        data = {
            'order': {
                'instrument': instrument,
                'units': units if side == 'BUY' else -units,
                'type': 'MARKET',
                'timeInForce': 'FOK'
            }
        }
        if sl_pips:
            data['order']['stopLossOnFill'] = {'distance': self._round_sl_tp_distance(sl_pips, instrument)}
        if tp_pips:
            data['order']['takeProfitOnFill'] = {'distance': self._round_sl_tp_distance(tp_pips, instrument)}
        
        try:
            r = orders.OrderCreate(accountID=self.account_id, data=data)
            response = self._rate_limited_request(r)
            
            # Parse order response
            order_info = self.order_response_handler.parse_order_response(response)
            
            # Handle partial fills
            if order_info['fill_status'] == 'PARTIAL_FILL':
                action = self.order_response_handler.handle_partial_fill(
                    order_info, abs(units), strategy=PARTIAL_FILL_STRATEGY
                )
                logging.warning(f"Partial fill for {instrument}: {action['reason']}")
                if self.structured_logger:
                    self.structured_logger.log_order_result(
                        instrument, 'MARKET', 'PARTIAL_FILL',
                        action=action['action'],
                        filled_pct=f"{order_info['filled_units']/abs(units)*100:.1f}%"
                    )
            
            # Register position if successful
            if order_info['success'] and order_info['fill_status'] in ['FULL_FILL', 'PARTIAL_FILL']:
                self.risk_manager.register_position(instrument, order_info.get('filled_units', units), risk_amount)
                if self.performance_monitor:
                    self.performance_monitor.record_trade_attempt(True, None)
                logging.info(f"Order placed for {instrument}: {order_info['fill_status']}")
            else:
                if self.performance_monitor:
                    self.performance_monitor.record_trade_attempt(False, order_info.get('error', 'Unknown error'))
                logging.error(f"Order failed for {instrument}: {order_info.get('error', 'Unknown error')}")
            
            return response
        
        except Exception as e:
            logging.error(f"Exception placing order for {instrument}: {e}")
            if self.performance_monitor:
                self.performance_monitor.record_trade_attempt(False, f"Exception: {str(e)}")
            return None

    def scan_pairs_for_signals(self):
        """Scan pairs for signals with single-trade strategy focus."""
        signals = []
        atr_readings = []  # Collect ATR values for volatility detection
        
        # Get current threshold (adaptive or static)
        current_threshold = (self.adaptive_threshold_mgr.get_current_threshold() 
                           if self.enable_adaptive_threshold 
                           else CONFIDENCE_THRESHOLD)
        
        # Get currently open position instruments
        open_position_instruments = self.get_open_position_instruments()
        
        # SINGLE-TRADE STRATEGY: If we have an open position, focus exclusively on it
        if open_position_instruments and MAX_OPEN_POSITIONS == 1:
            print(f"🎯 SINGLE-TRADE MODE: Monitoring existing position {open_position_instruments[0]} - skipping new signal scan", flush=True)
            # Return empty signals - we're focused on the open trade
            return signals, atr_readings
        
        # No open positions, so scan for new opportunities
        pairs_to_scan = []
        selection_mode = "persistent"
        
        # Use persistent pairs if enabled
        if self.enable_persistent_pairs and self.persistent_pairs_mgr:
            # Initialize persistent pairs if empty
            if len(self.persistent_pairs_mgr) == 0:
                available_instruments = self._get_available_instruments()
                self.persistent_pairs_mgr.initialize_from_available(available_instruments)
            
            # Check if it's time to requalify pairs
            if self.persistent_pairs_mgr.should_requalify_pairs():
                print(f"🔄 Requalifying persistent pairs...", flush=True)
                # Get all pairs from manager (including disqualified ones for rechecking)
                all_pairs = list(self.persistent_pairs_mgr.pairs.keys())
                
                # Requalify each pair
                for pair in all_pairs:
                    try:
                        df = self.get_prices(pair, count=50, granularity=GRANULARITY)
                        qualified = self.persistent_pairs_mgr.check_pair_qualification(
                            pair, df, get_signal_with_confidence
                        )
                        self.persistent_pairs_mgr.update_pair_qualification(pair, qualified)
                    except Exception as e:
                        logging.warning(f"Failed to requalify {pair}: {e}")
                        self.persistent_pairs_mgr.update_pair_qualification(pair, False)
                
                # Log stats after requalification
                stats = self.persistent_pairs_mgr.get_stats()
                print(f"📊 Persistent pairs: {stats['qualified_pairs']}/{stats['total_pairs']} qualified", flush=True)
            
            # Get qualified pairs to scan
            pairs_to_scan = self.persistent_pairs_mgr.get_pairs_to_scan()
            selection_mode = "persistent"
        else:
            # Fallback to traditional scanning
            available_instruments = self._get_available_instruments()
            
            # For backward compatibility when persistent pairs disabled
            if open_position_instruments:
                pairs_to_scan = open_position_instruments[:MAX_OPEN_POSITIONS]
                selection_mode = "prioritized"
            
            remaining_slots = MAX_PAIRS_TO_SCAN - len(pairs_to_scan)
            if remaining_slots > 0:
                remaining_instruments = [inst for inst in available_instruments if inst not in pairs_to_scan]
                
                if self.enable_dynamic_instruments and len(remaining_instruments) > remaining_slots:
                    pairs_to_scan.extend(random.sample(remaining_instruments, remaining_slots))
                    selection_mode = "prioritized+random"
                else:
                    pairs_to_scan.extend(remaining_instruments[:remaining_slots])
                    selection_mode = "prioritized+sequential"
        
        # Display scan info
        print(f"Scanning {len(pairs_to_scan)} pairs for signals ({selection_mode} selection)... "
              f"(threshold: {current_threshold:.3f})", flush=True)
        
        # Fetch margin info once at the start for affordability pre-filter
        margin_info = None
        available_margin = None
        if ENABLE_AFFORDABILITY_FILTER:
            try:
                margin_info = self.get_margin_info()
                available_margin = margin_info['margin_available']
                logging.debug(f"Available margin for affordability checks: {available_margin:.2f}")
            except Exception as e:
                logging.warning(f"Failed to get margin info for affordability filter: {e}")
                # Disable filter for this cycle if we can't get margin info
                available_margin = None
        
        # Debug: Show the bot's thinking
        threshold_source = "adaptive" if self.enable_adaptive_threshold else "static"
        print(f"🤖 BOT DECISION: Using {threshold_source} threshold = {current_threshold:.3f}", flush=True)
        if self.enable_persistent_pairs:
            stats = self.persistent_pairs_mgr.get_stats()
            print(f"🤖 BOT DECISION: Using persistent pairs ({stats['qualified_pairs']} qualified)", flush=True)
        print(f"🤖 BOT DECISION: Scanning {len(pairs_to_scan)} pairs: {', '.join(pairs_to_scan)}", flush=True)
        
        for instrument in pairs_to_scan:
            try:
                # Debug: Show we're scanning this pair
                print(f"🔍 BOT DECISION: Scanning pair {instrument}...", flush=True)
                
                # Get primary timeframe data (M5)
                df_primary = self.get_prices(instrument, count=50, granularity=GRANULARITY)
                
                # Check if we have price data
                if df_primary.empty:
                    logging.debug(f"No price data for {instrument}, skipping")
                    continue
                
                # Affordability pre-filter: Skip instruments that are too expensive for current margin
                if ENABLE_AFFORDABILITY_FILTER and available_margin is not None:
                    current_price = df_primary['close'].iloc[-1]
                    is_affordable, reason = self._is_instrument_affordable(
                        instrument, current_price, available_margin
                    )
                    if not is_affordable:
                        print(f"   ✗ BOT DECISION: {instrument} - Skipped (unaffordable with current margin: {reason})", flush=True)
                        continue
                
                if STRATEGY == 'advanced_scalp':
                    # Get signal with confidence and ATR
                    signal, confidence, atr = get_signal_with_confidence(
                        df_primary, 
                        STRATEGY,
                        atr_period=ATR_PERIOD,
                        volume_ma_period=VOLUME_MA_PERIOD,
                        min_volume_ratio=MIN_VOLUME_RATIO
                    )
                else:
                    # Legacy strategy support
                    signal = get_signal(df_primary, STRATEGY)
                    confidence = 1.0 if signal else 0.0
                    atr = 0.0
                
                # Collect ATR for volatility detection
                if atr > 0:
                    atr_readings.append(atr)
                
                # Debug: Show initial signal detection result
                if signal:
                    print(f"   ✓ BOT DECISION: {instrument} generated {signal} signal with initial confidence {confidence:.3f}", flush=True)
                else:
                    print(f"   ✗ BOT DECISION: {instrument} - No signal detected", flush=True)
                
                # Multi-timeframe confirmation (if enabled and signal exists)
                if signal and self.enable_multiframe:
                    try:
                        print(f"   🔄 BOT DECISION: {instrument} - Checking multi-timeframe confirmation...", flush=True)
                        original_confidence = confidence
                        df_h1 = self.get_prices(instrument, count=50, granularity='H1')
                        signal, confidence, atr = self.mtf_analyzer.confirm_signal(
                            signal, confidence, atr, df_h1, STRATEGY
                        )
                        if confidence != original_confidence:
                            print(f"   🔄 BOT DECISION: {instrument} - Multi-timeframe adjusted confidence: {original_confidence:.3f} → {confidence:.3f}", flush=True)
                    except Exception as e:
                        logging.warning(f"Multi-timeframe analysis failed for {instrument}: {e}")
                
                # ML prediction boost (if enabled and signal exists)
                ml_prediction = 0.5  # Default neutral
                if signal and self.enable_ml and self.ml_predictor:
                    try:
                        print(f"   🧠 BOT DECISION: {instrument} - Applying ML prediction...", flush=True)
                        original_confidence = confidence
                        ml_prediction = self.ml_predictor.predict_probability(df_primary)
                        # Adjust confidence based on ML prediction
                        # Weight: 70% original confidence, 30% ML prediction
                        confidence = confidence * 0.7 + ml_prediction * 0.3
                        print(f"   🧠 BOT DECISION: {instrument} - ML prediction {ml_prediction:.2f}, adjusted confidence: {original_confidence:.3f} → {confidence:.3f}", flush=True)
                    except Exception as e:
                        logging.warning(f"ML prediction failed for {instrument}: {e}")
                
                if signal and confidence >= current_threshold:
                    signals.append({
                        'instrument': instrument,
                        'signal': signal,
                        'confidence': confidence,
                        'atr': atr,
                        'ml_prediction': ml_prediction,
                        'df': df_primary  # Keep for position sizing calculation
                    })
                    print(f"   ✅ BOT DECISION: {instrument} - {signal} signal ACCEPTED with confidence {confidence:.3f} (>= threshold {current_threshold:.3f})", flush=True)
                elif signal:
                    print(f"   ❌ BOT DECISION: {instrument} - {signal} signal REJECTED: confidence {confidence:.3f} < threshold {current_threshold:.3f}", flush=True)
                    
            except Exception as e:
                logging.error(f"Error scanning {instrument}: {e}")
                continue
        
        # Debug: Summary of scan results
        print(f"🎯 BOT DECISION: Scan complete - Found {len(signals)} qualifying signals out of {len(pairs_to_scan)} pairs scanned", flush=True)
        if signals:
            for sig in signals:
                print(f"   - {sig['instrument']}: {sig['signal']} (confidence: {sig['confidence']:.3f})", flush=True)
        
        # Store ATR readings for volatility detection
        # Return both signals and atr_readings
        return signals, atr_readings
    
    def get_best_signal(self, signals):
        """Select the best signal based on confidence score."""
        if not signals:
            print("🏆 BOT DECISION: No signals to choose from", flush=True)
            return None
        
        # Debug: Show the selection process
        print(f"🏆 BOT DECISION: Selecting best signal from {len(signals)} candidates...", flush=True)
        
        # Sort by confidence descending
        sorted_signals = sorted(signals, key=lambda x: x['confidence'], reverse=True)
        
        # Debug: Show ranking
        for i, sig in enumerate(sorted_signals, 1):
            print(f"   #{i}: {sig['instrument']} {sig['signal']} (confidence: {sig['confidence']:.3f})", flush=True)
        
        best = sorted_signals[0]
        
        print(f"🏆 BOT DECISION: Selected best signal - {best['instrument']} {best['signal']} (confidence: {best['confidence']:.3f})", flush=True)
        return best
    
    def calculate_atr_stops(self, atr, signal, instrument, stop_multiplier=None, profit_multiplier=None, 
                           confidence=None):
        """Calculate ATR-based stop loss and take profit in pips with confidence adjustments.
        
        Args:
            atr: ATR value in price units
            signal: Trading signal ('BUY' or 'SELL')
            instrument: Trading instrument (e.g., 'EUR_USD', 'USD_JPY')
            stop_multiplier: Optional override for ATR stop multiplier (for volatility adjustments)
            profit_multiplier: Optional override for ATR profit multiplier (for volatility adjustments)
            confidence: Optional confidence score (0.0-1.0) for stop loss adjustment
            
        Returns:
            tuple: (stop_loss_pips, take_profit_pips)
        """
        # Validate ATR value
        is_valid, error_msg, sanitized_atr = self.data_validator.validate_atr(atr, instrument)
        if not is_valid:
            logging.warning(f"ATR validation failed for {instrument}: {error_msg}, using fallback")
            if self.structured_logger:
                self.structured_logger.log_validation_error("atr", error_msg, instrument=instrument)
            return STOP_LOSS_PIPS, TAKE_PROFIT_PIPS
        
        # Use sanitized ATR value
        atr = sanitized_atr
        
        # Use provided multipliers or fall back to config defaults
        stop_mult = stop_multiplier if stop_multiplier is not None else ATR_STOP_MULTIPLIER
        profit_mult = profit_multiplier if profit_multiplier is not None else ATR_PROFIT_MULTIPLIER
        
        # CONFIDENCE-BASED STOP LOSS ADJUSTMENT
        # If confidence is high (>0.8) and signal is BUY (upward trend), loosen stop loss
        if confidence is not None and confidence >= HIGH_CONFIDENCE_THRESHOLD and signal == 'BUY':
            original_stop_mult = stop_mult
            stop_mult = stop_mult * HIGH_CONFIDENCE_SL_MULTIPLIER
            logging.info(f"🎯 High confidence {signal} signal ({confidence:.2f}) - loosening SL: "
                        f"{original_stop_mult:.2f}x -> {stop_mult:.2f}x ATR")
            print(f"🎯 HIGH CONFIDENCE ADJUSTMENT: SL multiplier {original_stop_mult:.2f}x -> {stop_mult:.2f}x "
                  f"for {signal} signal with confidence {confidence:.2f}", flush=True)
        
        # Dynamically determine pip size from instrument metadata
        pip_size = self._get_instrument_pip_size(instrument)
        
        if atr > 0:
            # Calculate price distances with potentially adjusted multipliers
            sl_price = atr * stop_mult
            tp_price = atr * profit_mult
            
            # Convert price distances to pips
            sl_pips = sl_price / pip_size
            tp_pips = tp_price / pip_size
            
            # Cap take profit at 50 pips to prevent 'Take profit out of reasonable range' errors
            if tp_pips > 50:
                logging.info(f"Take profit capped at 50 pips (was {tp_pips:.2f} pips) for {instrument}")
                tp_pips = 50
            
            return sl_pips, tp_pips
        else:
            # Fallback to config defaults (already in pips)
            return STOP_LOSS_PIPS, TAKE_PROFIT_PIPS
    
    def _round_sl_tp_distance(self, distance_pips, instrument):
        """Round SL/TP distance to appropriate decimal places based on instrument.
        
        Oanda requires that stop loss and take profit distances are specified with
        precision that matches the instrument's pip location. For example:
        - EUR_USD (pipLocation=-4): distances should have ~4-5 decimal places
        - USD_JPY (pipLocation=-2): distances should have ~2-3 decimal places
        - Commodities/indices may vary based on their pip location
        
        Args:
            distance_pips: Distance value in pips (can be float with high precision)
            instrument: Trading instrument name (e.g., 'EUR_USD', 'USD_JPY')
            
        Returns:
            str: Rounded distance as string suitable for Oanda API
        """
        # Get pip size for the instrument
        pip_size = self._get_instrument_pip_size(instrument)
        
        # Convert pips to price distance
        price_distance = distance_pips * pip_size
        
        # Determine precision based on pip location
        # Get displayPrecision from instrument metadata if available
        if instrument in self.instruments_cache:
            display_precision = self.instruments_cache[instrument].get('displayPrecision', 5)
        else:
            # Fallback: determine from pip size
            # pip_size = 0.0001 -> 4 decimals, pip_size = 0.01 -> 2 decimals
            if pip_size >= 0.01:
                display_precision = 2
            elif pip_size >= 0.001:
                display_precision = 3
            else:
                display_precision = 5
        
        # Round the price distance to display precision
        rounded_distance = round(price_distance, display_precision)
        
        # Format as string with appropriate precision
        # Use format to avoid scientific notation and trailing zeros
        return f"{rounded_distance:.{display_precision}f}"

    def get_open_positions_with_details(self):
        """
        Get detailed information about all open positions including current profit.
        
        Returns:
            list: List of dicts with position details including instrument, units, unrealized_pl, entry_price, etc.
        """
        try:
            r = positions.OpenPositions(accountID=self.account_id)
            response = self._rate_limited_request(r)
            api_positions = response.get('positions', [])
            
            detailed_positions = []
            for pos in api_positions:
                instrument = pos.get('instrument')
                if not instrument:
                    continue
                
                long_units = float(pos.get('long', {}).get('units', 0))
                short_units = float(pos.get('short', {}).get('units', 0))
                long_pl = float(pos.get('long', {}).get('unrealizedPL', 0))
                short_pl = float(pos.get('short', {}).get('unrealizedPL', 0))
                long_avg_price = float(pos.get('long', {}).get('averagePrice', 0)) if long_units != 0 else 0
                short_avg_price = float(pos.get('short', {}).get('averagePrice', 0)) if short_units != 0 else 0
                
                # Calculate net position
                net_units = long_units + short_units  # short_units is negative
                total_pl = long_pl + short_pl
                
                if net_units != 0:
                    # Determine entry price based on position direction
                    entry_price = long_avg_price if long_units != 0 else short_avg_price
                    
                    detailed_positions.append({
                        'instrument': instrument,
                        'units': net_units,
                        'unrealized_pl': total_pl,
                        'entry_price': entry_price,
                        'long_units': long_units,
                        'short_units': short_units,
                        'direction': 'BUY' if net_units > 0 else 'SELL'
                    })
            
            return detailed_positions
        
        except Exception as e:
            logging.error(f"Failed to get open positions with details: {e}")
            return []
    
    def should_close_position_at_profit(self, position, take_profit_pips):
        """
        Determine if a position should be closed based on current profit vs. take profit target.
        
        Args:
            position: Position dict with instrument, units, unrealized_pl, entry_price
            take_profit_pips: Take profit target in pips
            
        Returns:
            tuple: (should_close, reason, current_profit_pips)
        """
        instrument = position['instrument']
        unrealized_pl = position['unrealized_pl']
        units = abs(position['units'])
        entry_price = position['entry_price']
        
        if units == 0 or entry_price == 0:
            return False, "Invalid position data", 0
        
        # Calculate pip value for this instrument
        pip_value = self._calculate_pip_value(instrument, entry_price)
        
        # Calculate profit in pips
        # Formula: profit_pips = unrealized_pl / (units * pip_value)
        if pip_value > 0:
            current_profit_pips = unrealized_pl / (units * pip_value)
        else:
            return False, "Invalid pip value", 0
        
        # Check if current profit >= take profit target
        if current_profit_pips >= take_profit_pips:
            return True, f"Profit target reached: {current_profit_pips:.2f} pips >= {take_profit_pips:.2f} pips", current_profit_pips
        
        return False, f"Profit below target: {current_profit_pips:.2f} pips < {take_profit_pips:.2f} pips", current_profit_pips
    
    def close_position(self, instrument):
        """
        Close an open position for a specific instrument.
        
        Args:
            instrument: Trading instrument to close
            
        Returns:
            bool: True if position closed successfully, False otherwise
        """
        try:
            # Get current position details to determine close order
            r = positions.PositionDetails(accountID=self.account_id, instrument=instrument)
            response = self._rate_limited_request(r)
            
            long_units = float(response.get('position', {}).get('long', {}).get('units', 0))
            short_units = float(response.get('position', {}).get('short', {}).get('units', 0))
            
            # Prepare close order data
            data = {}
            
            if long_units > 0:
                data['longUnits'] = 'ALL'
            
            if short_units < 0:
                data['shortUnits'] = 'ALL'
            
            if not data:
                logging.warning(f"No position to close for {instrument}")
                return False
            
            # Close the position
            r = positions.PositionClose(accountID=self.account_id, instrument=instrument, data=data)
            response = self._rate_limited_request(r)
            
            logging.info(f"✅ Closed position for {instrument} via TP monitoring")
            
            # Unregister from risk manager
            if hasattr(self, 'risk_manager'):
                self.risk_manager.close_position(instrument)
            
            return True
        
        except Exception as e:
            logging.error(f"Failed to close position for {instrument}: {e}")
            return False
    
    def monitor_positions_for_take_profit(self):
        """
        Monitor all open positions and close them if take profit is reached.
        This runs in a separate thread and checks positions periodically.
        """
        logging.info(f"📊 Position monitoring started (interval: {self.position_monitor_interval}s)")
        
        while not self.position_monitor_stop_event.is_set():
            try:
                # Get all open positions with details
                positions_list = self.get_open_positions_with_details()
                
                if not positions_list:
                    # No open positions, just wait
                    self.position_monitor_stop_event.wait(self.position_monitor_interval)
                    continue
                
                logging.debug(f"📊 Monitoring {len(positions_list)} open positions for TP")
                
                for position in positions_list:
                    instrument = position['instrument']
                    
                    # Get the trade details from database to find the TP target
                    try:
                        conn = self.db.db_path
                        import sqlite3
                        conn = sqlite3.connect(self.db.db_path)
                        cursor = conn.cursor()
                        
                        # Get most recent open trade for this instrument
                        cursor.execute('''
                            SELECT take_profit, atr, stop_loss, entry_price 
                            FROM trades 
                            WHERE instrument = ? AND status = 'OPEN'
                            ORDER BY entry_time DESC 
                            LIMIT 1
                        ''', (instrument,))
                        
                        result = cursor.fetchone()
                        conn.close()
                        
                        if not result:
                            logging.debug(f"No open trade record found for {instrument}")
                            continue
                        
                        take_profit_pips, atr, stop_loss_pips, db_entry_price = result
                        
                        # Get current market price for trailing stop calculation
                        try:
                            df = self.get_prices(instrument, count=1, granularity=GRANULARITY)
                            current_price = df['close'].iloc[-1] if not df.empty else position['entry_price']
                        except:
                            current_price = position['entry_price']
                        
                        # Update trailing stop if enabled and profitable
                        if self.enable_trailing_stops and self.trailing_stop_manager and atr > 0:
                            # Get pip size for this instrument
                            pip_size = self._get_instrument_pip_size(instrument)
                            
                            # Calculate current stop loss price from entry price
                            if position['direction'] == 'BUY':
                                current_sl_price = db_entry_price - (stop_loss_pips * pip_size)
                            else:  # SELL
                                current_sl_price = db_entry_price + (stop_loss_pips * pip_size)
                            
                            # Try to update trailing stop
                            new_sl_price, move_amount_pips, should_update = self.trailing_stop_manager.calculate_new_stop_loss(
                                instrument=instrument,
                                direction=position['direction'],
                                entry_price=db_entry_price,
                                current_price=current_price,
                                current_sl_price=current_sl_price,
                                atr_pips=atr,
                                pip_size=pip_size
                            )
                            
                            if should_update:
                                # Update stop loss via API
                                try:
                                    # Get trade ID for this position
                                    r = positions.PositionDetails(accountID=self.account_id, instrument=instrument)
                                    pos_details = self._rate_limited_request(r)
                                    
                                    # Update SL by modifying the trade
                                    # Note: Oanda uses trade modifications for SL updates on existing positions
                                    # For simplicity, we'll log the trailing stop move
                                    # In production, you'd want to actually update the SL via API
                                    logging.info(f"🔒 Trailing stop updated for {instrument}: New SL at {new_sl_price:.5f} "
                                               f"(moved {move_amount_pips:.1f} pips in profit direction)")
                                    
                                    # Update database with new SL
                                    conn_update = sqlite3.connect(self.db.db_path)
                                    cursor_update = conn_update.cursor()
                                    new_sl_pips = abs(new_sl_price - db_entry_price) / pip_size
                                    cursor_update.execute('''
                                        UPDATE trades 
                                        SET stop_loss = ?
                                        WHERE instrument = ? AND status = 'OPEN'
                                    ''', (new_sl_pips, instrument))
                                    conn_update.commit()
                                    conn_update.close()
                                    
                                except Exception as e:
                                    logging.error(f"Failed to update trailing stop for {instrument}: {e}")
                        
                        # Check if we should close at profit
                        should_close, reason, current_profit_pips = self.should_close_position_at_profit(
                            position, take_profit_pips
                        )
                        
                        if should_close:
                            logging.info(f"🎯 Take profit reached for {instrument}: {reason}")
                            
                            # Close the position
                            if self.close_position(instrument):
                                # Clear trailing stop state
                                if self.enable_trailing_stops and self.trailing_stop_manager:
                                    self.trailing_stop_manager.clear_instrument_state(instrument)
                                
                                # Update trade status in database
                                conn = sqlite3.connect(self.db.db_path)
                                cursor = conn.cursor()
                                cursor.execute('''
                                    UPDATE trades 
                                    SET status = 'CLOSED_TP_MONITOR', 
                                        exit_time = CURRENT_TIMESTAMP,
                                        pnl = ?
                                    WHERE instrument = ? AND status = 'OPEN'
                                ''', (position['unrealized_pl'], instrument))
                                conn.commit()
                                conn.close()
                                
                                # Increment ML training counter
                                if self.enable_ml and self.ml_auto_train_interval:
                                    self.ml_trades_since_last_train += 1
                                
                                logging.info(f"✅ Position closed and database updated for {instrument}")
                        else:
                            logging.debug(f"📊 {instrument}: {reason}")
                    
                    except Exception as e:
                        logging.error(f"Error monitoring position for {instrument}: {e}")
                        continue
                
                # Wait for next check interval
                self.position_monitor_stop_event.wait(self.position_monitor_interval)
            
            except Exception as e:
                logging.error(f"Error in position monitoring loop: {e}")
                # Wait before retrying
                self.position_monitor_stop_event.wait(self.position_monitor_interval)
        
        logging.info("📊 Position monitoring stopped")
    
    def start_position_monitoring(self):
        """Start the position monitoring thread."""
        if not self.enable_position_monitoring:
            logging.info("Position monitoring is disabled in config")
            return
        
        if self.position_monitor_thread and self.position_monitor_thread.is_alive():
            logging.warning("Position monitoring thread is already running")
            return
        
        self.position_monitor_stop_event.clear()
        self.position_monitor_thread = threading.Thread(
            target=self.monitor_positions_for_take_profit,
            daemon=True,
            name="PositionMonitor"
        )
        self.position_monitor_thread.start()
        logging.info("✅ Position monitoring thread started")
    
    def stop_position_monitoring(self):
        """Stop the position monitoring thread."""
        if not self.position_monitor_thread:
            return
        
        logging.info("Stopping position monitoring thread...")
        self.position_monitor_stop_event.set()
        
        # Wait for thread to finish (with timeout)
        if self.position_monitor_thread.is_alive():
            self.position_monitor_thread.join(timeout=5)
        
        if self.position_monitor_thread.is_alive():
            logging.warning("Position monitoring thread did not stop cleanly")
        else:
            logging.info("✅ Position monitoring thread stopped")
        
        self.position_monitor_thread = None

    def run_cycle(self):
        print("DEBUG: Entering run_cycle", flush=True)
        cycle_start_time = time.time()
        
        # Periodic analytics report
        if self.enable_comprehensive_analytics and self.analytics_engine:
            if (self.last_analytics_report is None or 
                (datetime.now() - self.last_analytics_report).total_seconds() >= self.analytics_report_interval):
                try:
                    current_balance = self.get_balance()
                    report = self.analytics_engine.generate_comprehensive_report(days=30, current_balance=current_balance)
                    self.analytics_engine.print_report(report)
                    self.last_analytics_report = datetime.now()
                except Exception as e:
                    logging.error(f"Failed to generate analytics report: {e}")
        
        # Auto-train ML model if enabled
        if self.enable_ml and self.ml_predictor and self.ml_auto_train_interval:
            if self.ml_trades_since_last_train >= self.ml_auto_train_interval:
                try:
                    logging.info(f"🧠 Auto-training ML model after {self.ml_trades_since_last_train} new trades...")
                    # Get recent market data for training
                    import sqlite3
                    conn = sqlite3.connect(self.db.db_path)
                    cursor = conn.cursor()
                    cursor.execute('SELECT COUNT(*) FROM trades WHERE status LIKE "CLOSED%"')
                    total_closed = cursor.fetchone()[0]
                    conn.close()
                    
                    if total_closed >= ML_MIN_TRAINING_SAMPLES:
                        # Use any instrument's data for training (or combine multiple)
                        df_train = self.get_prices('EUR_USD', count=500, granularity=GRANULARITY)
                        if not df_train.empty:
                            self.ml_predictor.train(df_train, database=self.db)
                            self.ml_trades_since_last_train = 0
                            logging.info(f"✅ ML model retrained successfully with {total_closed} historical trades")
                        else:
                            logging.warning("Could not fetch training data for ML model")
                    else:
                        logging.info(f"Insufficient closed trades ({total_closed}/{ML_MIN_TRAINING_SAMPLES}) for ML training")
                        self.ml_trades_since_last_train = 0  # Reset to avoid repeated attempts
                except Exception as e:
                    logging.error(f"ML auto-training failed: {e}")
                    self.ml_trades_since_last_train = 0  # Reset counter on error
        
        # Periodic health check
        if ENABLE_HEALTH_CHECKS and self.performance_monitor:
            if (self.last_health_check is None or 
                (datetime.now() - self.last_health_check).total_seconds() >= HEALTH_CHECK_INTERVAL):
                self._perform_health_check()
                self.last_health_check = datetime.now()
        
        # Check daily loss limit first
        current_balance = self.get_balance()
        print(f"DEBUG: Current balance in run_cycle: {current_balance}", flush=True)
        
        # Check minimum balance threshold
        if current_balance < MIN_ACCOUNT_BALANCE:
            logging.error(f"Balance {current_balance:.2f} below minimum threshold {MIN_ACCOUNT_BALANCE}, stopping.")
            return False
        
        daily_loss_pct = (self.daily_start_balance - current_balance) / self.daily_start_balance
        
        if daily_loss_pct > MAX_DAILY_LOSS_PERCENT / 100:
            logging.error(f"Daily loss limit reached ({daily_loss_pct*100:.2f}%), stopping.")
            return False
        
        # Check margin availability
        if not self.check_margin():
            logging.warning("Insufficient margin available, skipping this cycle.")
            return True
        
        # Update position state from API
        if hasattr(self, 'risk_manager'):
            try:
                r = positions.OpenPositions(accountID=self.account_id)
                response = self._rate_limited_request(r)
                api_positions = response.get('positions', [])
                self.risk_manager.update_positions_from_api(api_positions)
            except Exception as e:
                logging.warning(f"Failed to update positions from API: {e}")
        
        # Scan all pairs for signals (now returns signals and atr_readings)
        signals, atr_readings = self.scan_pairs_for_signals()
        
        # Detect market volatility
        volatility_info = None
        threshold_adjusted = False
        stops_adjusted = False
        cycle_skipped = False
        
        if self.enable_volatility_detection and self.volatility_detector:
            volatility_info = self.volatility_detector.detect_volatility(atr_readings)
            
            # Check if we should skip this cycle due to low volatility
            skip_decision = self.volatility_detector.should_skip_cycle()
            if skip_decision['skip']:
                logging.info(f"⏸️  Skipping cycle due to low volatility: {skip_decision['reason']}")
                cycle_skipped = True
                
                # Store volatility reading in database
                if self.db:
                    vol_data = {
                        'avg_atr': volatility_info['avg_atr'],
                        'state': volatility_info['state'],
                        'confidence': volatility_info['confidence'],
                        'readings_count': volatility_info['readings_count'],
                        'consecutive_low_cycles': volatility_info.get('consecutive_low_cycles', 0),
                        'adjustment_mode': VOLATILITY_ADJUSTMENT_MODE,
                        'threshold_adjusted': False,
                        'stops_adjusted': False,
                        'cycle_skipped': True
                    }
                    self.db.store_volatility_reading(vol_data)
                
                return True  # Continue but skip this cycle
        
        # Update adaptive threshold based on signal frequency
        # (Note: adaptive threshold manager now uses volatility detector internally)
        if self.enable_adaptive_threshold:
            threshold_adjusted = self.adaptive_threshold_mgr.update_on_cycle(len(signals))
        
        if not signals:
            logging.info("No signals found in this cycle.")
            
            # Store volatility reading even when no signals
            if self.enable_volatility_detection and self.db and volatility_info:
                vol_data = {
                    'avg_atr': volatility_info['avg_atr'],
                    'state': volatility_info['state'],
                    'confidence': volatility_info['confidence'],
                    'readings_count': volatility_info['readings_count'],
                    'consecutive_low_cycles': volatility_info.get('consecutive_low_cycles', 0),
                    'adjustment_mode': VOLATILITY_ADJUSTMENT_MODE,
                    'threshold_adjusted': threshold_adjusted,
                    'stops_adjusted': False,
                    'cycle_skipped': False
                }
                self.db.store_volatility_reading(vol_data)
            
            return True
        
        # Get the best signal (highest confidence)
        best_signal = self.get_best_signal(signals)
        
        if best_signal:
            instrument = best_signal['instrument']
            signal = best_signal['signal']
            atr = best_signal['atr']
            confidence = best_signal['confidence']
            ml_prediction = best_signal.get('ml_prediction', 0.5)
            
            # Check for price gaps if enabled
            if DETECT_PRICE_GAPS and len(best_signal['df']) >= 2:
                current_price = best_signal['df']['close'].iloc[-1]
                previous_price = best_signal['df']['close'].iloc[-2]
                has_gap, gap_pct = self.data_validator.detect_price_gap(
                    current_price, previous_price, PRICE_GAP_THRESHOLD_PCT
                )
                if has_gap:
                    if SKIP_TRADING_ON_GAPS:
                        logging.warning(f"Large price gap detected for {instrument}: {gap_pct:.2f}%, skipping trade")
                        if self.structured_logger:
                            self.structured_logger.log_trade_decision(
                                instrument, signal, confidence, "SKIPPED",
                                f"Price gap {gap_pct:.2f}% exceeds threshold"
                            )
                        return True
                    else:
                        logging.warning(f"Large price gap detected for {instrument}: {gap_pct:.2f}%, proceeding with caution")
            
            # Get volatility-adjusted stop/profit multipliers if applicable
            stop_multiplier = ATR_STOP_MULTIPLIER
            profit_multiplier = ATR_PROFIT_MULTIPLIER
            
            if self.enable_volatility_detection and self.volatility_detector:
                sp_adjustment = self.volatility_detector.get_stop_profit_adjustment(
                    ATR_STOP_MULTIPLIER, ATR_PROFIT_MULTIPLIER
                )
                stop_multiplier = sp_adjustment['stop_multiplier']
                profit_multiplier = sp_adjustment['profit_multiplier']
                if stop_multiplier != ATR_STOP_MULTIPLIER or profit_multiplier != ATR_PROFIT_MULTIPLIER:
                    stops_adjusted = True
                    logging.info(f"🎯 Using volatility-adjusted multipliers: "
                               f"stop={stop_multiplier:.2f}x, profit={profit_multiplier:.2f}x")
            
            # Calculate ATR-based stops (returns pips) with adjusted multipliers and confidence
            sl, tp = self.calculate_atr_stops(atr, signal, instrument, stop_multiplier, profit_multiplier, 
                                              confidence=confidence)
            
            # Get current price for pip value calculation
            current_price = best_signal['df']['close'].iloc[-1]
            
            # Calculate pip value for this instrument
            pip_value = self._calculate_pip_value(instrument, current_price)
            
            # Get margin information for margin-based position sizing
            margin_info = self.get_margin_info()
            
            # Calculate optimal position size
            if ENABLE_AUTO_SCALE_UNITS:
                # Use auto-scaling to fit both margin and risk constraints
                logging.info(f"Using auto-scaling position sizing for {instrument}")
                
                # Get instrument metadata from cache
                inst_metadata = self.instruments_cache.get(instrument, {})
                margin_rate = inst_metadata.get('marginRate', 0.0333)
                minimum_trade_size = inst_metadata.get('minimumTradeSize', '1')
                trade_units_precision = inst_metadata.get('tradeUnitsPrecision', 0)
                maximum_order_units = inst_metadata.get('maximumOrderUnits', '100000000')
                
                units, risk_pct, debug = self.position_sizer.calculate_auto_scaled_units(
                    balance=current_balance,
                    stop_loss_pips=sl,
                    pip_value=pip_value,
                    current_price=current_price,
                    available_margin=margin_info['margin_available'],
                    margin_rate=margin_rate,
                    minimum_trade_size=minimum_trade_size,
                    trade_units_precision=trade_units_precision,
                    maximum_order_units=maximum_order_units,
                    risk_per_trade=MAX_RISK_PER_TRADE,
                    max_units_per_instrument=MAX_UNITS_PER_INSTRUMENT,
                    min_trade_value=MIN_TRADE_VALUE,
                    margin_buffer=AUTO_SCALE_MARGIN_BUFFER,
                    auto_scale_min_units=AUTO_SCALE_MIN_UNITS
                )
                
                # Log debug information
                logging.debug(f"Auto-scaling debug for {instrument}:")
                logging.debug(f"  effective_available_margin: ${debug.get('effective_available_margin', 0):.2f}")
                logging.debug(f"  units_by_margin: {debug.get('units_by_margin', 0)}")
                logging.debug(f"  units_by_risk: {debug.get('units_by_risk', 0)}")
                logging.debug(f"  candidate_units: {debug.get('candidate_units', 0)}")
                logging.debug(f"  min_trade_size: {debug.get('min_trade_size', 0)}")
                
                if units == 0:
                    # Skip this trade
                    skip_reason = debug.get('reason', 'Unknown reason')
                    logging.warning(f"Skipping trade for {instrument}: {skip_reason}")
                    if self.structured_logger:
                        self.structured_logger.log_trade_decision(
                            instrument, signal, confidence, "SKIPPED", skip_reason
                        )
                    return True
                
                logging.info(f"Auto-scaled position size for {instrument}: {units} units, "
                           f"risk={risk_pct*100:.2f}%, margin_rate={margin_rate:.4f}")
            else:
                # Use existing margin-based approach
                # This prevents INSUFFICIENT_MARGIN errors for leveraged instruments
                performance_metrics = self.db.get_performance_metrics(days=30)
                units, risk_pct = self.position_sizer.calculate_position_size(
                    balance=current_balance,
                    stop_loss_pips=sl,
                    pip_value=pip_value,
                    performance_metrics=performance_metrics,
                    confidence=confidence,
                    available_margin=margin_info['margin_available'],
                    current_price=current_price,
                    margin_buffer=MARGIN_BUFFER
                )
            
            logging.info(f"Placing order for {instrument}: {signal} with SL={sl:.4f}, TP={tp:.4f}, \
                        units={units}, risk={risk_pct*100:.2f}%, pip_value={pip_value:.4f}")
            
            # Calculate risk amount for final validation
            risk_amount = units * sl * pip_value
            
            # Final risk check using RiskManager (will be called again in place_order, but good to check early)
            can_open, reason = self.risk_manager.can_open_position(instrument, units, risk_amount, current_balance)
            if not can_open:
                logging.warning(f"Final risk check failed for {instrument}: {reason}")
                if self.structured_logger:
                    self.structured_logger.log_risk_check("position_limit", False, reason, instrument=instrument)
                return True
            
            # Place order with current price for risk calculation
            response = self.place_order(instrument, signal, units, sl, tp, current_price)
            
            # Store trade in database
            if response:
                entry_price = best_signal['df']['close'].iloc[-1]
                trade_data = {
                    'instrument': instrument,
                    'signal': signal,
                    'confidence': confidence,
                    'entry_price': entry_price,
                    'stop_loss': sl,
                    'take_profit': tp,
                    'units': units,
                    'atr': atr,
                    'ml_prediction': ml_prediction,
                    'position_size_pct': risk_pct
                }
                self.db.store_trade(trade_data)
                logging.info(f"Trade stored in database")
                
                # Update adaptive threshold based on recent performance
                if self.enable_adaptive_threshold:
                    # Get recent performance for threshold adjustment
                    perf = self.db.get_performance_metrics(days=7)
                    if perf['total_trades'] >= ADAPTIVE_MIN_TRADES_FOR_ADJUSTMENT:
                        # Note: We can't know if this specific trade is profitable yet
                        # So we use overall recent performance to adjust
                        self.adaptive_threshold_mgr.update_on_trade_result(
                            trade_profitable=None,  # Unknown yet
                            recent_performance=perf
                        )
                
                # Store volatility reading with trade execution context
                if self.enable_volatility_detection and self.db and volatility_info:
                    vol_data = {
                        'avg_atr': volatility_info['avg_atr'],
                        'state': volatility_info['state'],
                        'confidence': volatility_info['confidence'],
                        'readings_count': volatility_info['readings_count'],
                        'consecutive_low_cycles': volatility_info.get('consecutive_low_cycles', 0),
                        'adjustment_mode': VOLATILITY_ADJUSTMENT_MODE,
                        'threshold_adjusted': threshold_adjusted,
                        'stops_adjusted': stops_adjusted,
                        'cycle_skipped': False
                    }
                    self.db.store_volatility_reading(vol_data)
        
        # Record cycle metrics
        if self.performance_monitor:
            cycle_duration = time.time() - cycle_start_time
            self.performance_monitor.record_cycle(cycle_duration, len(signals))
        
        return True
    
    def _perform_health_check(self):
        """Perform comprehensive health check on bot components."""
        try:
            health_results = HealthChecker.perform_full_health_check(
                self.api, self.account_id, self.db, 
                self.get_balance(), MIN_ACCOUNT_BALANCE
            )
            
            if not health_results['overall']['healthy']:
                logging.warning("Health check failed:")
                for component, result in health_results.items():
                    if component != 'overall' and not result.get('healthy', True):
                        logging.warning(f"  - {component}: {result.get('message', 'Unknown issue')}")
            else:
                logging.info("Health check passed - all systems operational")
            
            # Log performance summary
            if self.performance_monitor:
                summary = self.performance_monitor.get_summary()
                logging.info(f"Performance: {summary['trade_metrics']['success_rate_pct']:.1f}% trade success, "
                           f"{summary['api_metrics']['error_rate_pct']:.1f}% API error rate")
                
                # Log risk summary
                if hasattr(self, 'risk_manager'):
                    balance = self.get_balance()
                    risk_summary = self.risk_manager.get_risk_summary(balance)
                    logging.info(f"Risk: {risk_summary['open_positions']}/{risk_summary['max_positions']} positions, "
                               f"{risk_summary['risk_capacity_used_pct']:.1f}% capacity used")
        
        except Exception as e:
            logging.error(f"Health check failed with exception: {e}")

    def run(self, interval=CHECK_INTERVAL):
        print(f"DEBUG: Entering run method with interval={interval}", flush=True)
        
        # Start position monitoring thread
        self.start_position_monitoring()
        
        try:
            while True:
                print("DEBUG: Starting new cycle iteration", flush=True)
                if not self.run_cycle():
                    print("DEBUG: run_cycle returned False, breaking loop", flush=True)
                    break
                print(f"DEBUG: Cycle completed, sleeping for {interval} seconds", flush=True)
                time.sleep(interval)
        finally:
            # Stop position monitoring thread when bot stops
            self.stop_position_monitoring()

if __name__ == '__main__':
    print("DEBUG: In main block, about to create OandaTradingBot", flush=True)
    bot = OandaTradingBot(enable_ml=False)
    print("DEBUG: Bot created successfully, about to call bot.run()", flush=True)
    bot.run()