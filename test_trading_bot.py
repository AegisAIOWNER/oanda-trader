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


if __name__ == '__main__':
    unittest.main()
