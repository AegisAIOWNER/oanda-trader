"""
Unit tests for future-proofing enhancements.
Tests validation, risk management, and monitoring modules.
"""
import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import tempfile
import os

# Import modules to test
from validation import DataValidator, RiskValidator
from risk_manager import RiskManager, OrderResponseHandler
from monitoring import StructuredLogger, PerformanceMonitor, HealthChecker
from database import TradeDatabase


class TestDataValidator(unittest.TestCase):
    """Test data validation functionality."""
    
    def setUp(self):
        """Create sample data for testing."""
        self.validator = DataValidator()
    
    def test_validate_valid_candle_data(self):
        """Test validation of valid candle data."""
        # Need at least 5 candles (MIN_CANDLES_REQUIRED default)
        data = {
            'time': ['2024-01-01T00:00:00Z', '2024-01-01T00:05:00Z', '2024-01-01T00:10:00Z',
                     '2024-01-01T00:15:00Z', '2024-01-01T00:20:00Z', '2024-01-01T00:25:00Z'],
            'open': [1.1000, 1.1005, 1.1010, 1.1015, 1.1020, 1.1025],
            'high': [1.1010, 1.1015, 1.1020, 1.1025, 1.1030, 1.1035],
            'low': [1.0990, 1.0995, 1.1000, 1.1005, 1.1010, 1.1015],
            'close': [1.1005, 1.1010, 1.1015, 1.1020, 1.1025, 1.1030],
            'volume': [100, 120, 110, 130, 115, 125]
        }
        df = pd.DataFrame(data)
        
        is_valid, message = self.validator.validate_candle_data(df, 'EUR_USD')
        self.assertTrue(is_valid)
        self.assertEqual(message, "Valid candle data")
    
    def test_validate_empty_candle_data(self):
        """Test validation of empty candle data."""
        df = pd.DataFrame()
        
        is_valid, message = self.validator.validate_candle_data(df, 'EUR_USD')
        self.assertFalse(is_valid)
        self.assertIn("No candle data", message)
    
    def test_validate_insufficient_candles(self):
        """Test validation with insufficient candles."""
        data = {
            'time': ['2024-01-01T00:00:00Z'],
            'open': [1.1000],
            'high': [1.1010],
            'low': [1.0990],
            'close': [1.1005],
            'volume': [100]
        }
        df = pd.DataFrame(data)
        
        is_valid, message = self.validator.validate_candle_data(df, 'EUR_USD', min_candles=5)
        self.assertFalse(is_valid)
        self.assertIn("Insufficient candles", message)
    
    def test_validate_invalid_ohlc_relationship(self):
        """Test detection of invalid OHLC relationships."""
        # Need at least 5 candles, make sure one has invalid OHLC
        data = {
            'time': ['2024-01-01T00:00:00Z', '2024-01-01T00:05:00Z', '2024-01-01T00:10:00Z',
                     '2024-01-01T00:15:00Z', '2024-01-01T00:20:00Z'],
            'open': [1.1000, 1.1005, 1.1010, 1.1015, 1.1020],
            'high': [1.1010, 1.1015, 1.1020, 1.0990, 1.1030],  # 4th high < open (invalid)
            'low': [1.0990, 1.0995, 1.1000, 1.0985, 1.1010],
            'close': [1.1005, 1.1010, 1.1015, 1.0995, 1.1025],
            'volume': [100, 120, 110, 130, 115]
        }
        df = pd.DataFrame(data)
        
        is_valid, message = self.validator.validate_candle_data(df, 'EUR_USD')
        self.assertFalse(is_valid)
        self.assertIn("Invalid OHLC relationships", message)
    
    def test_validate_nan_values(self):
        """Test detection of NaN values in candle data."""
        # Need at least 5 candles
        data = {
            'time': ['2024-01-01T00:00:00Z', '2024-01-01T00:05:00Z', '2024-01-01T00:10:00Z',
                     '2024-01-01T00:15:00Z', '2024-01-01T00:20:00Z'],
            'open': [np.nan, 1.1005, 1.1010, 1.1015, 1.1020],
            'high': [1.1010, 1.1015, 1.1020, 1.1025, 1.1030],
            'low': [1.0990, 1.0995, 1.1000, 1.1005, 1.1010],
            'close': [1.1005, 1.1010, 1.1015, 1.1020, 1.1025],
            'volume': [100, 120, 110, 130, 115]
        }
        df = pd.DataFrame(data)
        
        is_valid, message = self.validator.validate_candle_data(df, 'EUR_USD')
        self.assertFalse(is_valid)
        self.assertIn("NaN values", message)
    
    def test_validate_valid_atr(self):
        """Test validation of valid ATR value."""
        is_valid, message, sanitized = self.validator.validate_atr(0.0010, 'EUR_USD')
        self.assertTrue(is_valid)
        self.assertEqual(message, "Valid ATR")
        self.assertEqual(sanitized, 0.0010)
    
    def test_validate_zero_atr(self):
        """Test handling of zero ATR value."""
        is_valid, message, sanitized = self.validator.validate_atr(0.0, 'EUR_USD')
        self.assertTrue(is_valid)  # Valid but needs fallback
        self.assertIn("zero", message.lower())
        self.assertEqual(sanitized, 0.0)
    
    def test_validate_negative_atr(self):
        """Test rejection of negative ATR value."""
        is_valid, message, sanitized = self.validator.validate_atr(-0.0010, 'EUR_USD')
        self.assertFalse(is_valid)
        self.assertIn("negative", message.lower())
    
    def test_validate_nan_atr(self):
        """Test rejection of NaN ATR value."""
        is_valid, message, sanitized = self.validator.validate_atr(np.nan, 'EUR_USD')
        self.assertFalse(is_valid)
        self.assertIn("NaN", message)
    
    def test_validate_valid_order_params(self):
        """Test validation of valid order parameters."""
        is_valid, message = self.validator.validate_order_params(
            'EUR_USD', 1000, stop_loss_pips=10.0, take_profit_pips=20.0
        )
        self.assertTrue(is_valid)
        self.assertEqual(message, "Valid order parameters")
    
    def test_validate_invalid_units(self):
        """Test rejection of invalid units."""
        is_valid, message = self.validator.validate_order_params(
            'EUR_USD', 0, stop_loss_pips=10.0
        )
        self.assertFalse(is_valid)
        self.assertIn("below minimum", message)
    
    def test_validate_excessive_units(self):
        """Test rejection of excessive units."""
        is_valid, message = self.validator.validate_order_params(
            'EUR_USD', 2000000, max_units=1000000
        )
        self.assertFalse(is_valid)
        self.assertIn("exceeds maximum", message)
    
    def test_validate_invalid_stop_loss(self):
        """Test rejection of invalid stop loss."""
        is_valid, message = self.validator.validate_order_params(
            'EUR_USD', 1000, stop_loss_pips=-5.0
        )
        self.assertFalse(is_valid)
        self.assertIn("Stop loss must be positive", message)
    
    def test_market_closed_weekend(self):
        """Test market hours detection (note: this is time-dependent)."""
        # This test is informational - it checks the method works
        is_closed, reason = self.validator.is_market_closed(check_weekend=True)
        self.assertIsInstance(is_closed, bool)
        self.assertIsInstance(reason, str)
    
    def test_detect_price_gap(self):
        """Test price gap detection."""
        # Need a larger gap - 5% move
        has_gap, gap_pct = self.validator.detect_price_gap(1.1000, 1.0450, threshold_pct=2.0)
        self.assertTrue(has_gap)
        self.assertGreater(gap_pct, 2.0)
    
    def test_no_price_gap(self):
        """Test no gap when prices are close."""
        has_gap, gap_pct = self.validator.detect_price_gap(1.1000, 1.0990, threshold_pct=2.0)
        self.assertFalse(has_gap)
        self.assertLess(gap_pct, 2.0)
    
    def test_validate_valid_api_response(self):
        """Test validation of valid API response."""
        response = {'account': {'balance': '10000'}, 'data': [1, 2, 3]}
        is_valid, message = self.validator.validate_api_response(response)
        self.assertTrue(is_valid)
    
    def test_validate_api_error_response(self):
        """Test detection of API error response."""
        response = {'errorMessage': 'Invalid request'}
        is_valid, message = self.validator.validate_api_response(response)
        self.assertFalse(is_valid)
        self.assertIn("Invalid request", message)
    
    def test_validate_missing_keys(self):
        """Test detection of missing expected keys."""
        response = {'balance': '10000'}
        is_valid, message = self.validator.validate_api_response(
            response, expected_keys=['account', 'positions']
        )
        self.assertFalse(is_valid)
        self.assertIn("Missing expected keys", message)


class TestRiskValidator(unittest.TestCase):
    """Test risk validation functionality."""
    
    def setUp(self):
        """Create risk validator."""
        self.validator = RiskValidator(
            max_open_positions=3,
            max_risk_per_trade=0.02,
            max_total_risk=0.10,
            max_slippage_pips=2.0
        )
    
    def test_can_open_new_position(self):
        """Test opening new position within limits."""
        can_open, reason = self.validator.can_open_new_position(2)
        self.assertTrue(can_open)
    
    def test_cannot_open_exceeded_positions(self):
        """Test rejection when max positions reached."""
        can_open, reason = self.validator.can_open_new_position(3)
        self.assertFalse(can_open)
        self.assertIn("Maximum open positions", reason)
    
    def test_validate_position_risk_within_limits(self):
        """Test position risk within limits."""
        is_valid, message = self.validator.validate_position_risk(150, 10000)
        self.assertTrue(is_valid)
    
    def test_validate_position_risk_exceeded(self):
        """Test rejection when position risk exceeds limit."""
        is_valid, message = self.validator.validate_position_risk(300, 10000)
        self.assertFalse(is_valid)
        self.assertIn("exceeds maximum", message)
    
    def test_validate_total_exposure_within_limits(self):
        """Test total exposure within limits."""
        is_valid, message = self.validator.validate_total_exposure(200, 500, 10000)
        self.assertTrue(is_valid)
    
    def test_validate_total_exposure_exceeded(self):
        """Test rejection when total exposure exceeds limit."""
        is_valid, message = self.validator.validate_total_exposure(500, 600, 10000)
        self.assertFalse(is_valid)
        self.assertIn("Total risk exposure", message)
    
    def test_validate_acceptable_slippage(self):
        """Test acceptable slippage."""
        is_acceptable, slippage_pips, reason = self.validator.validate_slippage(
            1.1000, 1.1001, 'EUR_USD'
        )
        self.assertTrue(is_acceptable)
        self.assertLess(slippage_pips, 2.0)
    
    def test_validate_excessive_slippage(self):
        """Test rejection of excessive slippage."""
        is_acceptable, slippage_pips, reason = self.validator.validate_slippage(
            1.1000, 1.1005, 'EUR_USD'
        )
        self.assertFalse(is_acceptable)
        self.assertGreater(slippage_pips, 2.0)
        self.assertIn("exceeds maximum", reason)


class TestRiskManager(unittest.TestCase):
    """Test risk manager functionality."""
    
    def setUp(self):
        """Create risk manager."""
        self.manager = RiskManager(
            max_open_positions=3,
            max_risk_per_trade=0.02,
            max_total_risk=0.10,
            max_correlation_positions=2,
            max_units_per_instrument=100000
        )
    
    def test_initialization(self):
        """Test risk manager initialization."""
        self.assertEqual(self.manager.max_open_positions, 3)
        self.assertEqual(self.manager.position_count, 0)
        self.assertEqual(len(self.manager.open_positions), 0)
    
    def test_can_open_position_empty(self):
        """Test opening position when none exist."""
        can_open, reason = self.manager.can_open_position('EUR_USD', 1000, 100, 10000)
        self.assertTrue(can_open)
    
    def test_register_position(self):
        """Test registering a new position."""
        self.manager.register_position('EUR_USD', 1000, 100)
        self.assertEqual(self.manager.position_count, 1)
        self.assertIn('EUR_USD', self.manager.open_positions)
        self.assertEqual(self.manager.total_risk_amount, 100)
    
    def test_close_position(self):
        """Test closing a position."""
        self.manager.register_position('EUR_USD', 1000, 100)
        self.manager.close_position('EUR_USD')
        self.assertEqual(self.manager.position_count, 0)
        self.assertNotIn('EUR_USD', self.manager.open_positions)
        self.assertEqual(self.manager.total_risk_amount, 0)
    
    def test_max_positions_limit(self):
        """Test max positions limit."""
        self.manager.register_position('EUR_USD', 1000, 100)
        self.manager.register_position('GBP_USD', 1000, 100)
        self.manager.register_position('USD_JPY', 1000, 100)
        
        can_open, reason = self.manager.can_open_position('USD_CAD', 1000, 100, 10000)
        self.assertFalse(can_open)
        self.assertIn("Maximum open positions", reason)
    
    def test_duplicate_position_check(self):
        """Test rejection of duplicate position."""
        self.manager.register_position('EUR_USD', 1000, 100)
        
        can_open, reason = self.manager.can_open_position('EUR_USD', 1000, 100, 10000)
        self.assertFalse(can_open)
        self.assertIn("already open", reason)
    
    def test_max_units_per_instrument(self):
        """Test max units per instrument limit."""
        can_open, reason = self.manager.can_open_position('EUR_USD', 200000, 100, 10000)
        self.assertFalse(can_open)
        self.assertIn("exceeds maximum", reason)
    
    def test_correlation_limit(self):
        """Test correlation limit (same base currency)."""
        self.manager.register_position('EUR_USD', 1000, 100)
        self.manager.register_position('EUR_GBP', 1000, 100)
        
        can_open, reason = self.manager.can_open_position('EUR_JPY', 1000, 100, 10000)
        self.assertFalse(can_open)
        self.assertIn("Too many positions", reason)
    
    def test_get_risk_summary(self):
        """Test risk summary generation."""
        self.manager.register_position('EUR_USD', 1000, 150)
        self.manager.register_position('GBP_USD', 1000, 200)
        
        summary = self.manager.get_risk_summary(10000)
        
        self.assertEqual(summary['open_positions'], 2)
        self.assertEqual(summary['max_positions'], 3)
        self.assertEqual(summary['positions_available'], 1)
        self.assertEqual(summary['total_risk_amount'], 350)
        self.assertAlmostEqual(summary['total_risk_pct'], 3.5, places=1)
    
    def test_reset(self):
        """Test resetting risk manager state."""
        self.manager.register_position('EUR_USD', 1000, 100)
        self.manager.reset()
        
        self.assertEqual(self.manager.position_count, 0)
        self.assertEqual(len(self.manager.open_positions), 0)
        self.assertEqual(self.manager.total_risk_amount, 0.0)


class TestOrderResponseHandler(unittest.TestCase):
    """Test order response handling."""
    
    def setUp(self):
        """Create handler."""
        self.handler = OrderResponseHandler()
    
    def test_parse_full_fill_response(self):
        """Test parsing full fill response."""
        response = {
            'orderCreateTransaction': {'units': '1000'},
            'orderFillTransaction': {
                'id': '12345',
                'units': '1000',
                'price': '1.1000',
                'instrument': 'EUR_USD',
                'time': '2024-01-01T00:00:00Z',
                'pl': '0',
                'reason': 'MARKET_ORDER'
            }
        }
        
        order_info = self.handler.parse_order_response(response)
        
        self.assertTrue(order_info['success'])
        self.assertEqual(order_info['fill_status'], 'FULL_FILL')
        self.assertEqual(order_info['filled_units'], 1000)
        self.assertEqual(order_info['instrument'], 'EUR_USD')
    
    def test_parse_partial_fill_response(self):
        """Test parsing partial fill response."""
        response = {
            'orderCreateTransaction': {'units': '1000'},
            'orderFillTransaction': {
                'id': '12345',
                'units': '500',
                'price': '1.1000',
                'instrument': 'EUR_USD',
                'time': '2024-01-01T00:00:00Z',
                'pl': '0'
            }
        }
        
        order_info = self.handler.parse_order_response(response)
        
        self.assertTrue(order_info['success'])
        self.assertEqual(order_info['fill_status'], 'PARTIAL_FILL')
        self.assertEqual(order_info['requested_units'], 1000)
        self.assertEqual(order_info['filled_units'], 500)
    
    def test_parse_cancelled_response(self):
        """Test parsing cancelled order response."""
        response = {
            'orderCreateTransaction': {'units': '1000'},
            'orderCancelTransaction': {
                'orderID': '12345',
                'reason': 'INSUFFICIENT_LIQUIDITY'
            }
        }
        
        order_info = self.handler.parse_order_response(response)
        
        self.assertFalse(order_info['success'])
        self.assertEqual(order_info['fill_status'], 'CANCELLED')
        self.assertIn('INSUFFICIENT_LIQUIDITY', order_info['error'])
    
    def test_handle_partial_fill_accept(self):
        """Test accepting partial fill."""
        order_info = {
            'fill_status': 'PARTIAL_FILL',
            'filled_units': 600,
            'requested_units': 1000
        }
        
        action = self.handler.handle_partial_fill(order_info, 1000, strategy='ACCEPT')
        
        self.assertEqual(action['action'], 'ACCEPT')
        self.assertEqual(action['filled_units'], 600)
    
    def test_handle_partial_fill_cancel_small(self):
        """Test cancelling small partial fill."""
        order_info = {
            'fill_status': 'PARTIAL_FILL',
            'filled_units': 300,
            'requested_units': 1000
        }
        
        action = self.handler.handle_partial_fill(order_info, 1000, strategy='ACCEPT')
        
        self.assertEqual(action['action'], 'CANCEL')
        self.assertIn("too small", action['reason'])


class TestStructuredLogger(unittest.TestCase):
    """Test structured logging."""
    
    def test_initialization(self):
        """Test logger initialization."""
        logger = StructuredLogger(name='TestLogger')
        self.assertIsNotNone(logger.logger)
        self.assertEqual(logger.context, {})
    
    def test_set_context(self):
        """Test setting context."""
        logger = StructuredLogger(name='TestLogger')
        logger.set_context(instrument='EUR_USD', signal='BUY')
        
        self.assertEqual(logger.context['instrument'], 'EUR_USD')
        self.assertEqual(logger.context['signal'], 'BUY')
    
    def test_clear_context(self):
        """Test clearing context."""
        logger = StructuredLogger(name='TestLogger')
        logger.set_context(instrument='EUR_USD')
        logger.clear_context()
        
        self.assertEqual(logger.context, {})
    
    def test_log_trade_decision(self):
        """Test trade decision logging (should not raise exception)."""
        logger = StructuredLogger(name='TestLogger')
        logger.log_trade_decision('EUR_USD', 'BUY', 0.85, 'PLACED', 'High confidence')
        # If we get here without exception, test passes
        self.assertTrue(True)


class TestPerformanceMonitor(unittest.TestCase):
    """Test performance monitoring."""
    
    def setUp(self):
        """Create performance monitor."""
        self.monitor = PerformanceMonitor(window_size=10)
    
    def test_initialization(self):
        """Test monitor initialization."""
        self.assertEqual(self.monitor.api_success_count, 0)
        self.assertEqual(self.monitor.api_error_count, 0)
        self.assertEqual(self.monitor.trade_attempts, 0)
    
    def test_record_successful_api_call(self):
        """Test recording successful API call."""
        self.monitor.record_api_call(True, 0.5, None)
        
        self.assertEqual(self.monitor.api_success_count, 1)
        self.assertEqual(self.monitor.api_error_count, 0)
        self.assertIsNotNone(self.monitor.last_successful_api_call)
    
    def test_record_failed_api_call(self):
        """Test recording failed API call."""
        self.monitor.record_api_call(False, 0.5, Exception("Test error"))
        
        self.assertEqual(self.monitor.api_success_count, 0)
        self.assertEqual(self.monitor.api_error_count, 1)
        self.assertEqual(len(self.monitor.api_errors), 1)
    
    def test_record_trade_success(self):
        """Test recording successful trade."""
        self.monitor.record_trade_attempt(True, None)
        
        self.assertEqual(self.monitor.trade_attempts, 1)
        self.assertEqual(self.monitor.trade_successes, 1)
        self.assertEqual(self.monitor.trade_failures, 0)
    
    def test_record_trade_failure(self):
        """Test recording failed trade."""
        self.monitor.record_trade_attempt(False, "Risk limit exceeded")
        
        self.assertEqual(self.monitor.trade_attempts, 1)
        self.assertEqual(self.monitor.trade_successes, 0)
        self.assertEqual(self.monitor.trade_failures, 1)
        self.assertEqual(self.monitor.trades_rejected_by_risk, 1)
    
    def test_record_cycle(self):
        """Test recording cycle."""
        self.monitor.record_cycle(5.2, 3)
        
        self.assertEqual(len(self.monitor.cycle_times), 1)
        self.assertEqual(len(self.monitor.signals_found), 1)
        self.assertIsNotNone(self.monitor.last_cycle_time)
    
    def test_get_api_metrics(self):
        """Test getting API metrics."""
        self.monitor.record_api_call(True, 0.5, None)
        self.monitor.record_api_call(True, 0.6, None)
        self.monitor.record_api_call(False, 0.7, Exception("Error"))
        
        metrics = self.monitor.get_api_metrics()
        
        self.assertEqual(metrics['total_calls'], 3)
        self.assertEqual(metrics['success_count'], 2)
        self.assertEqual(metrics['error_count'], 1)
        self.assertAlmostEqual(metrics['error_rate_pct'], 33.33, places=1)
    
    def test_get_health_status_healthy(self):
        """Test health status when healthy."""
        self.monitor.record_api_call(True, 0.5, None)
        
        health = self.monitor.get_health_status()
        
        self.assertEqual(health['status'], 'HEALTHY')
        self.assertTrue(health['api_healthy'])
        self.assertTrue(health['error_rate_healthy'])
    
    def test_get_health_status_high_error_rate(self):
        """Test health status with high error rate."""
        # Record many failed calls
        for _ in range(8):
            self.monitor.record_api_call(False, 0.5, Exception("Error"))
        for _ in range(2):
            self.monitor.record_api_call(True, 0.5, None)
        
        health = self.monitor.get_health_status()
        
        self.assertEqual(health['status'], 'DEGRADED')
        self.assertFalse(health['error_rate_healthy'])


class TestHealthChecker(unittest.TestCase):
    """Test health checker functionality."""
    
    def test_check_balance_sufficient_above_threshold(self):
        """Test balance check when balance is above minimum."""
        is_healthy, message = HealthChecker.check_balance_sufficient(150, min_balance=100)
        self.assertTrue(is_healthy)
        self.assertIn("150.00", message)
    
    def test_check_balance_sufficient_at_threshold(self):
        """Test balance check when balance equals minimum."""
        is_healthy, message = HealthChecker.check_balance_sufficient(100, min_balance=100)
        self.assertTrue(is_healthy)
        self.assertIn("100.00", message)
    
    def test_check_balance_insufficient_below_threshold(self):
        """Test balance check when balance is below minimum."""
        is_healthy, message = HealthChecker.check_balance_sufficient(50, min_balance=100)
        self.assertFalse(is_healthy)
        self.assertIn("50.00", message)
        self.assertIn("100.00", message)
    
    def test_check_balance_with_practice_threshold(self):
        """Test balance check with practice mode threshold."""
        # Practice mode should allow lower balance (10)
        is_healthy, message = HealthChecker.check_balance_sufficient(15, min_balance=10)
        self.assertTrue(is_healthy)
        self.assertIn("15.00", message)
        
        is_healthy, message = HealthChecker.check_balance_sufficient(5, min_balance=10)
        self.assertFalse(is_healthy)
        self.assertIn("5.00", message)
        self.assertIn("10.00", message)


class TestConfigurationValues(unittest.TestCase):
    """Test configuration values for single-trade strategy."""
    
    def test_max_risk_per_trade_config_value(self):
        """Test that MAX_RISK_PER_TRADE is set to 0.1 (10%) for single-trade strategy."""
        import config
        
        # Verify MAX_RISK_PER_TRADE is set to 0.1 (10%)
        self.assertEqual(config.MAX_RISK_PER_TRADE, 0.1, 
                        "MAX_RISK_PER_TRADE should be 0.1 (10%) for focused single-trade strategy")
        
    def test_max_risk_per_trade_validator_accepts_10_percent(self):
        """Test that RiskValidator correctly validates trades at 10% risk."""
        # Create validator with 10% max risk
        validator = RiskValidator(
            max_open_positions=1,
            max_risk_per_trade=0.1,  # 10%
            max_total_risk=0.15,
            max_slippage_pips=2.0
        )
        
        # Test that 10% risk is accepted
        balance = 10000
        risk_amount = 1000  # 10% of 10000
        is_valid, message = validator.validate_position_risk(risk_amount, balance)
        self.assertTrue(is_valid, f"10% risk should be valid: {message}")
        
        # Test that 11% risk is rejected
        risk_amount = 1100  # 11% of 10000
        is_valid, message = validator.validate_position_risk(risk_amount, balance)
        self.assertFalse(is_valid, "11% risk should be rejected")
        self.assertIn("exceeds maximum", message)


if __name__ == '__main__':
    unittest.main()
