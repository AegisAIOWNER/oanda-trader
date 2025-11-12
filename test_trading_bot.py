"""
Unit tests for the trading bot key functions.
"""
import unittest
import pandas as pd
import numpy as np
from datetime import datetime
import os
import tempfile

# Import modules to test
from strategies import calculate_indicators, advanced_scalp
from position_sizing import PositionSizer
from ml_predictor import MLPredictor
from multi_timeframe import MultiTimeframeAnalyzer
from database import TradeDatabase
from error_recovery import ExponentialBackoff, CircuitBreaker
from backtest import calculate_sharpe_ratio, calculate_max_drawdown
import oandapyV20.endpoints.instruments as instruments


class TestInstrumentsEndpoint(unittest.TestCase):
    """Test that bot uses the correct Oanda API endpoint class."""
    
    def test_instruments_candles_class_exists(self):
        """Test that InstrumentsCandles class exists in instruments module."""
        self.assertTrue(hasattr(instruments, 'InstrumentsCandles'))
    
    def test_instruments_candles_instantiation(self):
        """Test that InstrumentsCandles can be instantiated correctly."""
        params = {'count': 50, 'granularity': 'M5'}
        r = instruments.InstrumentsCandles(instrument='EUR_USD', params=params)
        
        # Verify the object is created
        self.assertIsNotNone(r)
        self.assertEqual(type(r).__name__, 'InstrumentsCandles')
    
    def test_instruments_candles_not_instruments_candles(self):
        """Test that instruments.Candles does NOT exist (confirming the bug fix)."""
        self.assertFalse(hasattr(instruments, 'Candles'))


class TestStrategies(unittest.TestCase):
    """Test trading strategies."""
    
    def setUp(self):
        """Create sample data for testing."""
        np.random.seed(42)
        n = 50
        base_price = 1.1000
        prices = base_price + np.cumsum(np.random.randn(n) * 0.0001)
        
        self.sample_df = pd.DataFrame({
            'open': prices + np.random.randn(n) * 0.00005,
            'high': prices + abs(np.random.randn(n) * 0.0001),
            'low': prices - abs(np.random.randn(n) * 0.0001),
            'close': prices,
            'volume': np.random.randint(100, 1000, n)
        })
    
    def test_calculate_indicators(self):
        """Test indicator calculation."""
        df_with_indicators = calculate_indicators(self.sample_df)
        
        self.assertIsNotNone(df_with_indicators)
        self.assertIn('rsi', df_with_indicators.columns)
        self.assertIn('macd', df_with_indicators.columns)
        self.assertIn('atr', df_with_indicators.columns)
        self.assertIn('bb_upper', df_with_indicators.columns)
        self.assertIn('volume_ratio', df_with_indicators.columns)
    
    def test_advanced_scalp_signal(self):
        """Test advanced scalp strategy signal generation."""
        signal, confidence, atr = advanced_scalp(self.sample_df)
        
        # Signal can be 'BUY', 'SELL', or None
        self.assertIn(signal, ['BUY', 'SELL', None])
        
        # Confidence should be between 0 and 1
        self.assertGreaterEqual(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)
        
        # ATR should be non-negative
        self.assertGreaterEqual(atr, 0.0)


class TestATRStopsCalculation(unittest.TestCase):
    """Test ATR-based stop loss and take profit calculation."""
    
    def setUp(self):
        """Set up a mock bot for testing."""
        # We need to mock the bot to avoid API calls
        # Import here to avoid circular import issues
        from unittest.mock import MagicMock, patch
        from bot import OandaTradingBot
        
        # Mock the API and database to avoid actual connections
        with patch('bot.oandapyV20.API'), \
             patch('bot.TradeDatabase'), \
             patch('bot.MLPredictor'), \
             patch('bot.PositionSizer'), \
             patch('bot.MultiTimeframeAnalyzer'), \
             patch('bot.AdaptiveThresholdManager'), \
             patch.object(OandaTradingBot, 'get_balance', return_value=10000.0):
            self.bot = OandaTradingBot(
                enable_ml=False, 
                enable_multiframe=False,
                enable_adaptive_threshold=False
            )
    
    def test_calculate_atr_stops_eur_usd(self):
        """Test ATR stops calculation for EUR_USD (standard pair)."""
        atr = 0.0002  # ATR in price units
        signal = 'BUY'
        instrument = 'EUR_USD'
        
        sl_pips, tp_pips = self.bot.calculate_atr_stops(atr, signal, instrument)
        
        # With ATR_STOP_MULTIPLIER = 0.5 and ATR_PROFIT_MULTIPLIER = 1.5
        # sl_price = 0.0002 * 0.5 = 0.0001
        # tp_price = 0.0002 * 1.5 = 0.0003
        # For EUR_USD, pip_size = 0.0001
        # sl_pips = 0.0001 / 0.0001 = 1.0
        # BUT: minimum 10 pips is enforced, so sl_pips = 10.0
        # tp_pips = 0.0003 / 0.0001 = 3.0
        
        self.assertAlmostEqual(sl_pips, 10.0, places=5)  # Enforced minimum
        self.assertAlmostEqual(tp_pips, 3.0, places=5)
    
    def test_calculate_atr_stops_usd_jpy(self):
        """Test ATR stops calculation for USD_JPY (JPY pair)."""
        atr = 0.15  # ATR in price units (JPY pairs have different scale)
        signal = 'SELL'
        instrument = 'USD_JPY'
        
        sl_pips, tp_pips = self.bot.calculate_atr_stops(atr, signal, instrument)
        
        # With ATR_STOP_MULTIPLIER = 0.5 and ATR_PROFIT_MULTIPLIER = 1.5
        # sl_price = 0.15 * 0.5 = 0.075
        # tp_price = 0.15 * 1.5 = 0.225
        # For USD_JPY, pip_size = 0.01
        # sl_pips = 0.075 / 0.01 = 7.5
        # BUT: minimum 10 pips is enforced, so sl_pips = 10.0
        # tp_pips = 0.225 / 0.01 = 22.5
        
        self.assertAlmostEqual(sl_pips, 10.0, places=5)  # Enforced minimum
        self.assertAlmostEqual(tp_pips, 22.5, places=5)
    
    def test_calculate_atr_stops_gbp_usd(self):
        """Test ATR stops calculation for GBP_USD (standard pair)."""
        atr = 0.0004
        signal = 'BUY'
        instrument = 'GBP_USD'
        
        sl_pips, tp_pips = self.bot.calculate_atr_stops(atr, signal, instrument)
        
        # With ATR_STOP_MULTIPLIER = 0.5 and ATR_PROFIT_MULTIPLIER = 1.5
        # sl_price = 0.0004 * 0.5 = 0.0002
        # tp_price = 0.0004 * 1.5 = 0.0006
        # For GBP_USD, pip_size = 0.0001
        # sl_pips = 0.0002 / 0.0001 = 2.0
        # BUT: minimum 10 pips is enforced, so sl_pips = 10.0
        # tp_pips = 0.0006 / 0.0001 = 6.0
        
        self.assertAlmostEqual(sl_pips, 10.0, places=5)  # Enforced minimum
        self.assertAlmostEqual(tp_pips, 6.0, places=5)
    
    def test_calculate_atr_stops_zero_atr(self):
        """Test fallback to config defaults when ATR is zero."""
        from config import STOP_LOSS_PIPS, TAKE_PROFIT_PIPS
        
        atr = 0.0
        signal = 'BUY'
        instrument = 'EUR_USD'
        
        sl_pips, tp_pips = self.bot.calculate_atr_stops(atr, signal, instrument)
        
        # Should return config defaults
        self.assertEqual(sl_pips, STOP_LOSS_PIPS)
        self.assertEqual(tp_pips, TAKE_PROFIT_PIPS)
    
    def test_calculate_atr_stops_eur_jpy(self):
        """Test ATR stops calculation for EUR_JPY (JPY pair)."""
        atr = 0.12
        signal = 'BUY'
        instrument = 'EUR_JPY'
        
        sl_pips, tp_pips = self.bot.calculate_atr_stops(atr, signal, instrument)
        
        # With ATR_STOP_MULTIPLIER = 0.5 and ATR_PROFIT_MULTIPLIER = 1.5
        # sl_price = 0.12 * 0.5 = 0.06
        # tp_price = 0.12 * 1.5 = 0.18
        # For EUR_JPY, pip_size = 0.01 (contains JPY)
        # sl_pips = 0.06 / 0.01 = 6.0
        # BUT: minimum 10 pips is enforced, so sl_pips = 10.0
        # tp_pips = 0.18 / 0.01 = 18.0
        
        self.assertAlmostEqual(sl_pips, 10.0, places=5)  # Enforced minimum
        self.assertAlmostEqual(tp_pips, 18.0, places=5)
    
    def test_pip_size_detection_various_instruments(self):
        """Test pip size detection for various instruments."""
        # Standard pairs (0.0001 pip size)
        standard_pairs = ['EUR_USD', 'GBP_USD', 'USD_CAD', 'AUD_USD', 'NZD_USD', 'EUR_GBP', 'USD_CHF']
        atr = 0.0001
        
        for instrument in standard_pairs:
            sl_pips, tp_pips = self.bot.calculate_atr_stops(atr, 'BUY', instrument)
            # With ATR_STOP_MULTIPLIER = 0.5:
            # sl_price = 0.0001 * 0.5 = 0.00005
            # sl_pips = 0.00005 / 0.0001 = 0.5
            # BUT: minimum 10 pips is enforced, so sl_pips = 10.0
            self.assertAlmostEqual(sl_pips, 10.0, places=5, 
                                 msg=f"Failed for {instrument}")
        
        # JPY pairs (0.01 pip size)
        jpy_pairs = ['USD_JPY', 'EUR_JPY', 'GBP_JPY', 'AUD_JPY']
        atr = 0.01
        
        for instrument in jpy_pairs:
            sl_pips, tp_pips = self.bot.calculate_atr_stops(atr, 'BUY', instrument)
            # With ATR_STOP_MULTIPLIER = 0.5:
            # sl_price = 0.01 * 0.5 = 0.005
            # sl_pips = 0.005 / 0.01 = 0.5
            # BUT: minimum 10 pips is enforced, so sl_pips = 10.0
            self.assertAlmostEqual(sl_pips, 10.0, places=5,
                                 msg=f"Failed for {instrument}")
    
    def test_take_profit_cap_at_50_pips(self):
        """Test that take profit is capped at 50 pips to prevent 'out of reasonable range' errors."""
        # Test case 1: High ATR that would normally produce >50 pips TP
        # EUR_USD with high ATR and large profit multiplier
        atr = 0.0050  # 50 pips worth of ATR
        signal = 'BUY'
        instrument = 'EUR_USD'
        profit_multiplier = 2.0  # Would result in 100 pips without cap
        
        sl_pips, tp_pips = self.bot.calculate_atr_stops(
            atr, signal, instrument, 
            profit_multiplier=profit_multiplier
        )
        
        # TP should be capped at 50 pips
        self.assertEqual(tp_pips, 50, msg="TP should be capped at 50 pips")
        
        # Test case 2: Very high volatility scenario
        atr = 0.0100  # 100 pips worth of ATR
        profit_multiplier = 3.0  # Would result in 300 pips without cap
        
        sl_pips, tp_pips = self.bot.calculate_atr_stops(
            atr, signal, instrument, 
            profit_multiplier=profit_multiplier
        )
        
        # TP should still be capped at 50 pips
        self.assertEqual(tp_pips, 50, msg="TP should be capped at 50 pips even with very high ATR")
        
        # Test case 3: Normal scenario that doesn't trigger cap
        atr = 0.0002  # 2 pips worth of ATR
        profit_multiplier = 1.5  # Would result in 3 pips
        
        sl_pips, tp_pips = self.bot.calculate_atr_stops(
            atr, signal, instrument, 
            profit_multiplier=profit_multiplier
        )
        
        # TP should NOT be capped (should be ~3 pips)
        self.assertLess(tp_pips, 50, msg="TP should not be capped for normal ATR values")
        self.assertAlmostEqual(tp_pips, 3.0, places=5)
        
        # Test case 4: Edge case exactly at 50 pips
        atr = 0.0050  # 50 pips
        profit_multiplier = 1.0  # Results in exactly 50 pips
        
        sl_pips, tp_pips = self.bot.calculate_atr_stops(
            atr, signal, instrument, 
            profit_multiplier=profit_multiplier
        )
        
        # TP should be exactly 50 pips (not capped, naturally at limit)
        self.assertEqual(tp_pips, 50, msg="TP should be 50 pips when naturally at limit")
    
    def test_minimum_stop_loss_10_pips_enforcement(self):
        """Test that stop loss is enforced to be at least 10 pips."""
        # Test case 1: Very small ATR that would produce less than 10 pips SL
        atr = 0.0001  # 1 pip worth of ATR for EUR_USD
        signal = 'BUY'
        instrument = 'EUR_USD'
        stop_multiplier = 0.5  # Would result in 0.5 pips without enforcement
        
        sl_pips, tp_pips = self.bot.calculate_atr_stops(
            atr, signal, instrument,
            stop_multiplier=stop_multiplier
        )
        
        # SL should be enforced to minimum 10 pips
        self.assertGreaterEqual(sl_pips, 10.0, msg="SL should be at least 10 pips")
        self.assertEqual(sl_pips, 10.0, msg="SL should be exactly 10 pips when below minimum")
        
        # Test case 2: ATR that would naturally produce exactly 10 pips
        atr = 0.0010  # 10 pips for EUR_USD
        stop_multiplier = 1.0  # Results in exactly 10 pips
        
        sl_pips, tp_pips = self.bot.calculate_atr_stops(
            atr, signal, instrument,
            stop_multiplier=stop_multiplier
        )
        
        # SL should be exactly 10 pips (not adjusted)
        self.assertAlmostEqual(sl_pips, 10.0, places=5, msg="SL should be 10 pips when naturally at minimum")
        
        # Test case 3: ATR that produces more than 10 pips (should not be adjusted)
        atr = 0.0020  # 20 pips for EUR_USD
        stop_multiplier = 1.0  # Results in 20 pips
        
        sl_pips, tp_pips = self.bot.calculate_atr_stops(
            atr, signal, instrument,
            stop_multiplier=stop_multiplier
        )
        
        # SL should remain at calculated value (20 pips)
        self.assertAlmostEqual(sl_pips, 20.0, places=5, msg="SL should not be adjusted when above minimum")
        
        # Test case 4: USD_JPY with very small ATR
        atr = 0.005  # 0.5 pips for USD_JPY
        instrument = 'USD_JPY'
        
        sl_pips, tp_pips = self.bot.calculate_atr_stops(
            atr, signal, instrument,
            stop_multiplier=stop_multiplier
        )
        
        # SL should be enforced to minimum 10 pips
        self.assertGreaterEqual(sl_pips, 10.0, msg="SL should be at least 10 pips for USD_JPY")
        self.assertEqual(sl_pips, 10.0, msg="SL should be exactly 10 pips when below minimum for USD_JPY")
        
        # Test case 5: Edge case with ATR exactly producing 9.99 pips
        atr = 0.000999  # 9.99 pips for EUR_USD
        instrument = 'EUR_USD'
        stop_multiplier = 1.0
        
        sl_pips, tp_pips = self.bot.calculate_atr_stops(
            atr, signal, instrument,
            stop_multiplier=stop_multiplier
        )
        
        # SL should be adjusted to 10 pips
        self.assertGreaterEqual(sl_pips, 10.0, msg="SL should be at least 10 pips even at 9.99")


class TestPositionSizing(unittest.TestCase):
    """Test position sizing calculations."""
    
    def setUp(self):
        self.balance = 10000.0
        self.stop_loss_pips = 0.001
    
    def test_fixed_percentage_sizing(self):
        """Test fixed percentage position sizing."""
        sizer = PositionSizer(method='fixed_percentage', risk_per_trade=0.02)
        
        units = sizer.calculate_fixed_percentage(
            balance=self.balance,
            stop_loss_pips=self.stop_loss_pips,
            pip_value=10
        )
        
        self.assertGreater(units, 0)
        self.assertIsInstance(units, int)
    
    def test_kelly_criterion(self):
        """Test Kelly Criterion calculation."""
        sizer = PositionSizer(method='kelly_criterion', kelly_fraction=0.25)
        
        kelly_pct = sizer.calculate_kelly_criterion(
            win_rate=0.6,
            avg_win=100,
            avg_loss=50
        )
        
        self.assertGreaterEqual(kelly_pct, 0.0)
        self.assertLessEqual(kelly_pct, 1.0)
    
    def test_position_size_with_confidence(self):
        """Test position sizing with confidence adjustment."""
        sizer = PositionSizer(method='fixed_percentage', risk_per_trade=0.02)
        
        units, risk_pct = sizer.calculate_position_size(
            balance=self.balance,
            stop_loss_pips=self.stop_loss_pips,
            pip_value=10,
            confidence=0.8
        )
        
        self.assertGreater(units, 0)
        self.assertGreater(risk_pct, 0)
        self.assertLessEqual(risk_pct, 0.02)


class TestMLPredictor(unittest.TestCase):
    """Test ML predictor."""
    
    def setUp(self):
        """Create sample training data."""
        np.random.seed(42)
        n = 200
        base_price = 1.1000
        prices = base_price + np.cumsum(np.random.randn(n) * 0.0001)
        
        self.sample_df = pd.DataFrame({
            'open': prices + np.random.randn(n) * 0.00005,
            'high': prices + abs(np.random.randn(n) * 0.0001),
            'low': prices - abs(np.random.randn(n) * 0.0001),
            'close': prices,
            'volume': np.random.randint(100, 1000, n),
            'rsi': np.random.rand(n) * 100,
            'macd': np.random.randn(n) * 0.0001,
            'macd_signal': np.random.randn(n) * 0.0001,
            'atr': np.random.rand(n) * 0.0001,
            'bb_upper': prices + 0.0001,
            'bb_lower': prices - 0.0001
        })
        
        # Use temporary file for model
        self.temp_model_file = tempfile.NamedTemporaryFile(suffix='.pkl', delete=False)
        self.model_path = self.temp_model_file.name
        self.temp_model_file.close()
    
    def tearDown(self):
        """Clean up temporary model file."""
        if os.path.exists(self.model_path):
            os.remove(self.model_path)
    
    def test_feature_engineering(self):
        """Test feature engineering."""
        predictor = MLPredictor(model_path=self.model_path)
        features = predictor._engineer_features(self.sample_df)
        
        self.assertIn('price_change', features.columns)
        self.assertIn('high_low_range', features.columns)
        self.assertIn('close_position_in_range', features.columns)
    
    def test_model_training(self):
        """Test model training."""
        predictor = MLPredictor(model_path=self.model_path)
        metrics = predictor.train(self.sample_df)
        
        self.assertIsNotNone(metrics)
        self.assertIn('accuracy', metrics)
        self.assertIn('precision', metrics)
        self.assertGreaterEqual(metrics['accuracy'], 0.0)
        self.assertLessEqual(metrics['accuracy'], 1.0)
    
    def test_prediction(self):
        """Test prediction after training."""
        predictor = MLPredictor(model_path=self.model_path)
        predictor.train(self.sample_df)
        
        prob = predictor.predict_probability(self.sample_df)
        
        self.assertGreaterEqual(prob, 0.0)
        self.assertLessEqual(prob, 1.0)


class TestMultiTimeframe(unittest.TestCase):
    """Test multi-timeframe analysis."""
    
    def setUp(self):
        """Create sample data for different timeframes."""
        np.random.seed(42)
        n = 50
        base_price = 1.1000
        prices = base_price + np.cumsum(np.random.randn(n) * 0.0001)
        
        self.m5_data = pd.DataFrame({
            'open': prices + np.random.randn(n) * 0.00005,
            'high': prices + abs(np.random.randn(n) * 0.0001),
            'low': prices - abs(np.random.randn(n) * 0.0001),
            'close': prices,
            'volume': np.random.randint(100, 1000, n)
        })
        
        self.h1_data = self.m5_data.copy()
    
    def test_trend_direction(self):
        """Test trend direction detection."""
        analyzer = MultiTimeframeAnalyzer()
        trend = analyzer.get_trend_direction(self.h1_data)
        
        self.assertIn(trend, ['BUY', 'SELL', None])
    
    def test_signal_confirmation(self):
        """Test signal confirmation with higher timeframe."""
        analyzer = MultiTimeframeAnalyzer()
        
        confirmed_signal, confidence, atr = analyzer.confirm_signal(
            primary_signal='BUY',
            primary_confidence=0.8,
            primary_atr=0.0001,
            confirmation_df=self.h1_data
        )
        
        # Confidence can be adjusted up or down
        self.assertGreaterEqual(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)


class TestDatabase(unittest.TestCase):
    """Test database operations."""
    
    def setUp(self):
        """Create temporary database."""
        self.temp_db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db_file.name
        self.temp_db_file.close()
        
        self.db = TradeDatabase(db_path=self.db_path)
    
    def tearDown(self):
        """Clean up database."""
        self.db.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
    
    def test_store_trade(self):
        """Test storing a trade."""
        trade_data = {
            'instrument': 'EUR_USD',
            'signal': 'BUY',
            'confidence': 0.85,
            'entry_price': 1.1000,
            'stop_loss': 0.001,
            'take_profit': 0.002,
            'units': 1000,
            'atr': 0.0001
        }
        
        trade_id = self.db.store_trade(trade_data)
        self.assertIsNotNone(trade_id)
        self.assertGreater(trade_id, 0)
    
    def test_get_performance_metrics(self):
        """Test performance metrics calculation."""
        # Store some sample trades
        for i in range(5):
            trade_data = {
                'instrument': 'EUR_USD',
                'signal': 'BUY',
                'confidence': 0.85,
                'entry_price': 1.1000 + i * 0.001,
                'units': 1000,
                'atr': 0.0001
            }
            trade_id = self.db.store_trade(trade_data)
            
            # Close some trades
            if i % 2 == 0:
                self.db.update_trade(trade_id, 1.1010, 10.0, 'closed')
        
        metrics = self.db.get_performance_metrics(days=30)
        
        self.assertIn('total_trades', metrics)
        self.assertIn('win_rate', metrics)


class TestErrorRecovery(unittest.TestCase):
    """Test error recovery mechanisms."""
    
    def test_exponential_backoff_success(self):
        """Test successful execution with backoff."""
        backoff = ExponentialBackoff(base_delay=0.1, max_retries=3)
        
        call_count = [0]
        
        def succeeds_on_second_try():
            call_count[0] += 1
            if call_count[0] < 2:
                raise Exception("Temporary failure")
            return "Success"
        
        result = backoff.execute_with_retry(succeeds_on_second_try)
        self.assertEqual(result, "Success")
        self.assertEqual(call_count[0], 2)
    
    def test_exponential_backoff_failure(self):
        """Test exhausting all retries."""
        backoff = ExponentialBackoff(base_delay=0.1, max_retries=3)
        
        def always_fails():
            raise Exception("Permanent failure")
        
        with self.assertRaises(Exception):
            backoff.execute_with_retry(always_fails)
    
    def test_circuit_breaker(self):
        """Test circuit breaker pattern."""
        breaker = CircuitBreaker(failure_threshold=3, timeout=1)
        
        def failing_function():
            raise Exception("Failure")
        
        # Fail enough times to open circuit
        for i in range(3):
            try:
                breaker.call(failing_function)
            except:
                pass
        
        # Circuit should be open
        self.assertEqual(breaker.state, 'open')
        
        # Next call should fail immediately
        with self.assertRaises(Exception) as context:
            breaker.call(failing_function)
        
        self.assertIn("Circuit breaker is open", str(context.exception))


class TestBacktesting(unittest.TestCase):
    """Test backtesting utilities."""
    
    def test_sharpe_ratio(self):
        """Test Sharpe ratio calculation."""
        # Generate sample returns
        np.random.seed(42)
        returns = pd.Series(np.random.randn(100) * 0.01)
        
        sharpe = calculate_sharpe_ratio(returns)
        
        self.assertIsInstance(sharpe, float)
        # Sharpe ratio should be reasonable for random data
        self.assertGreater(sharpe, -5)
        self.assertLess(sharpe, 5)
    
    def test_max_drawdown(self):
        """Test maximum drawdown calculation."""
        # Create equity curve with known drawdown
        equity = [10000, 10500, 10200, 9800, 9500, 10000, 11000]
        
        max_dd = calculate_max_drawdown(equity)
        
        self.assertGreaterEqual(max_dd, 0.0)
        self.assertLessEqual(max_dd, 1.0)
        # Known drawdown from 10500 to 9500 = 9.5%
        self.assertAlmostEqual(max_dd, 0.0952, places=3)


class TestAdaptiveThreshold(unittest.TestCase):
    """Test adaptive threshold management."""
    
    def setUp(self):
        """Create temporary database and adaptive threshold manager."""
        from adaptive_threshold import AdaptiveThresholdManager
        
        self.temp_db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db_file.name
        self.db = TradeDatabase(db_path=self.db_path)
        
        self.manager = AdaptiveThresholdManager(
            base_threshold=0.8,
            db=self.db,
            min_threshold=0.5,
            max_threshold=0.95,
            no_signal_cycles_trigger=5,
            adjustment_step=0.02
        )
    
    def tearDown(self):
        """Clean up temporary database."""
        self.db.close()
        os.unlink(self.db_path)
    
    def test_initialization(self):
        """Test manager initialization."""
        self.assertEqual(self.manager.current_threshold, 0.8)
        self.assertEqual(self.manager.base_threshold, 0.8)
        self.assertEqual(self.manager.min_threshold, 0.5)
        self.assertEqual(self.manager.max_threshold, 0.95)
    
    def test_lower_threshold_on_no_signals(self):
        """Test threshold lowering when no signals found."""
        initial_threshold = self.manager.current_threshold
        
        # Simulate cycles without signals
        for i in range(5):
            adjusted = self.manager.update_on_cycle(signals_found=0)
        
        # Threshold should be lowered after 5 cycles
        self.assertLess(self.manager.current_threshold, initial_threshold)
        self.assertEqual(self.manager.cycles_without_signal, 0)  # Reset after adjustment
    
    def test_reset_counter_on_signals(self):
        """Test counter reset when signals are found."""
        # Simulate cycles without signals
        for i in range(3):
            self.manager.update_on_cycle(signals_found=0)
        
        self.assertEqual(self.manager.cycles_without_signal, 3)
        
        # Find signals - should reset counter
        self.manager.update_on_cycle(signals_found=2)
        self.assertEqual(self.manager.cycles_without_signal, 0)
    
    def test_raise_threshold_on_good_performance(self):
        """Test threshold raising on strong performance."""
        initial_threshold = self.manager.current_threshold
        
        performance = {
            'win_rate': 0.70,
            'profit_factor': 1.8,
            'total_trades': 10
        }
        
        adjusted = self.manager.update_on_trade_result(
            trade_profitable=True,
            recent_performance=performance
        )
        
        # Threshold should be raised for strong performance
        self.assertTrue(adjusted)
        self.assertGreater(self.manager.current_threshold, initial_threshold)
    
    def test_raise_threshold_on_poor_performance(self):
        """Test threshold raising on poor performance to be more selective."""
        initial_threshold = self.manager.current_threshold
        
        performance = {
            'win_rate': 0.40,
            'profit_factor': 0.7,
            'total_trades': 10
        }
        
        adjusted = self.manager.update_on_trade_result(
            trade_profitable=False,
            recent_performance=performance
        )
        
        # Threshold should be raised for poor performance
        self.assertTrue(adjusted)
        self.assertGreater(self.manager.current_threshold, initial_threshold)
    
    def test_lower_threshold_on_marginal_performance(self):
        """Test threshold lowering on marginal performance."""
        initial_threshold = self.manager.current_threshold
        
        performance = {
            'win_rate': 0.52,
            'profit_factor': 1.05,
            'total_trades': 10
        }
        
        adjusted = self.manager.update_on_trade_result(
            trade_profitable=True,
            recent_performance=performance
        )
        
        # Threshold should be lowered for marginal performance
        self.assertTrue(adjusted)
        self.assertLess(self.manager.current_threshold, initial_threshold)
    
    def test_threshold_bounds(self):
        """Test threshold stays within min/max bounds."""
        # Try to lower below minimum
        self.manager.current_threshold = 0.52
        for i in range(10):
            self.manager.update_on_cycle(signals_found=0)
        
        self.assertGreaterEqual(self.manager.current_threshold, self.manager.min_threshold)
        
        # Reset and try to raise above maximum
        self.manager.current_threshold = 0.93
        performance = {
            'win_rate': 0.80,
            'profit_factor': 2.5,
            'total_trades': 10
        }
        
        for i in range(5):
            self.manager.update_on_trade_result(True, performance)
        
        self.assertLessEqual(self.manager.current_threshold, self.manager.max_threshold)
    
    def test_no_adjustment_with_insufficient_trades(self):
        """Test no performance-based adjustment with too few trades."""
        initial_threshold = self.manager.current_threshold
        
        performance = {
            'win_rate': 0.70,
            'profit_factor': 1.8,
            'total_trades': 3  # Below minimum
        }
        
        adjusted = self.manager.update_on_trade_result(
            trade_profitable=True,
            recent_performance=performance
        )
        
        self.assertFalse(adjusted)
        self.assertEqual(self.manager.current_threshold, initial_threshold)
    
    def test_adjustment_stored_in_database(self):
        """Test threshold adjustments are stored in database."""
        # Trigger an adjustment
        for i in range(5):
            self.manager.update_on_cycle(signals_found=0)
        
        # Check database has the adjustment
        adjustments = self.db.get_recent_threshold_adjustments(limit=1)
        self.assertEqual(len(adjustments), 1)
        self.assertEqual(adjustments[0]['old_threshold'], 0.8)
        self.assertLess(adjustments[0]['new_threshold'], 0.8)
        self.assertIn('cycles without signals', adjustments[0]['adjustment_reason'])
    
    def test_get_status(self):
        """Test status reporting."""
        status = self.manager.get_status()
        
        self.assertIn('current_threshold', status)
        self.assertIn('base_threshold', status)
        self.assertIn('cycles_without_signal', status)
        self.assertEqual(status['current_threshold'], 0.8)
    
    def test_reset_to_base(self):
        """Test manual reset to base threshold."""
        # Change threshold
        self.manager.current_threshold = 0.65
        self.manager.cycles_without_signal = 3
        
        # Reset
        self.manager.reset_to_base()
        
        self.assertEqual(self.manager.current_threshold, 0.8)
        self.assertEqual(self.manager.cycles_without_signal, 0)


class TestDynamicInstruments(unittest.TestCase):
    """Test dynamic instrument selection functionality."""
    
    def setUp(self):
        """Set up a mock bot for testing."""
        from unittest.mock import MagicMock, patch
        from bot import OandaTradingBot
        
        # Mock the API response for instruments
        self.mock_instruments_response = {
            'instruments': [
                {
                    'name': 'EUR_USD',
                    'displayName': 'EUR/USD',
                    'type': 'CURRENCY',
                    'pipLocation': -4,
                    'displayPrecision': 5,
                    'tradeUnitsPrecision': 0,
                    'minimumTradeSize': '1',
                    'maximumOrderUnits': '100000000'
                },
                {
                    'name': 'USD_JPY',
                    'displayName': 'USD/JPY',
                    'type': 'CURRENCY',
                    'pipLocation': -2,
                    'displayPrecision': 3,
                    'tradeUnitsPrecision': 0,
                    'minimumTradeSize': '1',
                    'maximumOrderUnits': '100000000'
                },
                {
                    'name': 'XAU_USD',
                    'displayName': 'Gold',
                    'type': 'METAL',
                    'pipLocation': -1,
                    'displayPrecision': 2,
                    'tradeUnitsPrecision': 0,
                    'minimumTradeSize': '1',
                    'maximumOrderUnits': '10000000'
                },
                {
                    'name': 'SPX500_USD',
                    'displayName': 'S&P 500',
                    'type': 'CFD',
                    'pipLocation': -1,
                    'displayPrecision': 2,
                    'tradeUnitsPrecision': 0,
                    'minimumTradeSize': '1',
                    'maximumOrderUnits': '100000'
                }
            ]
        }
        
        # Mock the API to return our test instruments
        with patch('bot.oandapyV20.API'), \
             patch('bot.TradeDatabase'), \
             patch('bot.MLPredictor'), \
             patch('bot.PositionSizer'), \
             patch('bot.MultiTimeframeAnalyzer'), \
             patch('bot.AdaptiveThresholdManager'), \
             patch('bot.VolatilityDetector'), \
             patch.object(OandaTradingBot, 'get_balance', return_value=10000.0), \
             patch.object(OandaTradingBot, '_rate_limited_request', return_value=self.mock_instruments_response):
            self.bot = OandaTradingBot(
                enable_ml=False, 
                enable_multiframe=False,
                enable_adaptive_threshold=False
            )
    
    def test_instruments_cached_on_init(self):
        """Test that instruments are cached during initialization."""
        self.assertEqual(len(self.bot.instruments_cache), 4)
        self.assertIn('EUR_USD', self.bot.instruments_cache)
        self.assertIn('USD_JPY', self.bot.instruments_cache)
        self.assertIn('XAU_USD', self.bot.instruments_cache)
        self.assertIn('SPX500_USD', self.bot.instruments_cache)
    
    def test_pip_size_from_cache(self):
        """Test pip size extraction from cached instruments."""
        # EUR_USD with pipLocation -4
        pip_size = self.bot._get_instrument_pip_size('EUR_USD')
        self.assertEqual(pip_size, 0.0001)
        
        # USD_JPY with pipLocation -2
        pip_size = self.bot._get_instrument_pip_size('USD_JPY')
        self.assertEqual(pip_size, 0.01)
        
        # XAU_USD (Gold) with pipLocation -1
        pip_size = self.bot._get_instrument_pip_size('XAU_USD')
        self.assertEqual(pip_size, 0.1)
        
        # SPX500_USD (S&P 500) with pipLocation -1
        pip_size = self.bot._get_instrument_pip_size('SPX500_USD')
        self.assertEqual(pip_size, 0.1)
    
    def test_get_available_instruments(self):
        """Test getting available instruments list."""
        instruments = self.bot._get_available_instruments()
        self.assertEqual(len(instruments), 4)
        self.assertIn('EUR_USD', instruments)
        self.assertIn('XAU_USD', instruments)
    
    def test_calculate_atr_stops_with_dynamic_pip_size(self):
        """Test ATR stops calculation with dynamically determined pip sizes."""
        # Test with Gold (XAU_USD) which has pipLocation -1
        atr = 1.5
        signal = 'BUY'
        instrument = 'XAU_USD'
        
        sl_pips, tp_pips = self.bot.calculate_atr_stops(atr, signal, instrument)
        
        # pip_size = 0.1 (from pipLocation -1)
        # sl_price = 1.5 * 1.0 = 1.5
        # tp_price = 1.5 * 1.5 = 2.25
        # sl_pips = 1.5 / 0.1 = 15.0
        # tp_pips = 2.25 / 0.1 = 22.5
        
        self.assertAlmostEqual(sl_pips, 15.0, places=5)
        self.assertAlmostEqual(tp_pips, 22.5, places=5)
    
    def test_fallback_to_legacy_pip_logic(self):
        """Test fallback to legacy logic for uncached instruments."""
        # Test with an instrument not in cache
        pip_size = self.bot._get_instrument_pip_size('GBP_CHF')
        
        # Should fall back to legacy logic (no JPY, so 0.0001)
        self.assertEqual(pip_size, 0.0001)
        
        # Test JPY pair fallback
        pip_size = self.bot._get_instrument_pip_size('EUR_JPY')
        self.assertEqual(pip_size, 0.01)
    
    def test_cache_metadata(self):
        """Test that all relevant metadata is cached."""
        eur_usd_meta = self.bot.instruments_cache['EUR_USD']
        
        self.assertEqual(eur_usd_meta['displayName'], 'EUR/USD')
        self.assertEqual(eur_usd_meta['type'], 'CURRENCY')
        self.assertEqual(eur_usd_meta['pipLocation'], -4)
        self.assertEqual(eur_usd_meta['displayPrecision'], 5)
        self.assertEqual(eur_usd_meta['minimumTradeSize'], '1')
    
    def test_on_demand_instrument_fetching(self):
        """Test that instruments are fetched on-demand when not in cache."""
        from unittest.mock import patch
        
        # Add GBP_JPY to the mock response (simulating it being available in API)
        extended_response = {
            'instruments': self.mock_instruments_response['instruments'] + [
                {
                    'name': 'GBP_JPY',
                    'displayName': 'GBP/JPY',
                    'type': 'CURRENCY',
                    'pipLocation': -2,
                    'displayPrecision': 3,
                    'tradeUnitsPrecision': 0,
                    'minimumTradeSize': '1',
                    'maximumOrderUnits': '100000000'
                }
            ]
        }
        
        # Ensure GBP_JPY is not in cache initially
        if 'GBP_JPY' in self.bot.instruments_cache:
            del self.bot.instruments_cache['GBP_JPY']
        
        # Mock the rate_limited_request to return extended response
        with patch.object(self.bot, '_rate_limited_request', return_value=extended_response):
            pip_size = self.bot._get_instrument_pip_size('GBP_JPY')
        
        # Should fetch from API and get correct pip size
        self.assertEqual(pip_size, 0.01)
        
        # Should now be cached
        self.assertIn('GBP_JPY', self.bot.instruments_cache)
        self.assertEqual(self.bot.instruments_cache['GBP_JPY']['pipLocation'], -2)


if __name__ == '__main__':
    unittest.main()
