"""
Unit tests for real-time position monitoring feature.
"""
import unittest
import time
import sqlite3
import tempfile
import os
from unittest.mock import MagicMock, patch, Mock
from datetime import datetime


class TestPositionMonitoring(unittest.TestCase):
    """Test position monitoring functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary database for testing
        self.db_fd, self.db_path = tempfile.mkstemp()
        
        # Mock the bot with minimal setup
        with patch('bot.oandapyV20.API'), \
             patch('bot.TradeDatabase') as mock_db, \
             patch('bot.MLPredictor'), \
             patch('bot.PositionSizer'), \
             patch('bot.MultiTimeframeAnalyzer'), \
             patch('bot.AdaptiveThresholdManager'), \
             patch('bot.VolatilityDetector'), \
             patch('bot.DataValidator'), \
             patch('bot.RiskValidator'), \
             patch('bot.RiskManager'), \
             patch('bot.StructuredLogger'), \
             patch('bot.PerformanceMonitor'):
            
            # Set up mock database
            mock_db.return_value.db_path = self.db_path
            
            # Import after patching
            from bot import OandaTradingBot
            
            # Create bot instance with position monitoring enabled
            with patch.object(OandaTradingBot, 'get_balance', return_value=10000.0):
                with patch.object(OandaTradingBot, '_fetch_and_cache_instruments'):
                    self.bot = OandaTradingBot(
                        enable_ml=False,
                        enable_multiframe=False,
                        enable_adaptive_threshold=False,
                        enable_volatility_detection=False
                    )
                    self.bot.db.db_path = self.db_path
        
        # Create test database schema
        self._create_test_db()
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Stop monitoring thread if running
        if hasattr(self.bot, 'position_monitor_thread') and self.bot.position_monitor_thread:
            self.bot.stop_position_monitoring()
        
        # Close and remove temporary database
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def _create_test_db(self):
        """Create test database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instrument TEXT NOT NULL,
                signal TEXT NOT NULL,
                confidence REAL,
                entry_price REAL,
                stop_loss REAL,
                take_profit REAL,
                units INTEGER,
                atr REAL,
                ml_prediction REAL,
                position_size_pct REAL,
                entry_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                exit_price REAL,
                exit_time TIMESTAMP,
                pnl REAL,
                status TEXT DEFAULT 'OPEN'
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _insert_test_trade(self, instrument, take_profit_pips=10.0, status='OPEN'):
        """Insert a test trade into the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO trades (
                instrument, signal, confidence, entry_price, stop_loss, 
                take_profit, units, atr, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (instrument, 'BUY', 0.85, 1.1000, 5.0, take_profit_pips, 1000, 0.0005, status))
        
        conn.commit()
        conn.close()
    
    def test_get_open_positions_with_details(self):
        """Test getting open positions with detailed information."""
        # Mock API response
        mock_response = {
            'positions': [
                {
                    'instrument': 'EUR_USD',
                    'long': {
                        'units': '1000',
                        'unrealizedPL': '15.50',
                        'averagePrice': '1.1000'
                    },
                    'short': {
                        'units': '0',
                        'unrealizedPL': '0',
                        'averagePrice': '0'
                    }
                }
            ]
        }
        
        with patch.object(self.bot, '_rate_limited_request', return_value=mock_response):
            positions = self.bot.get_open_positions_with_details()
            
            self.assertEqual(len(positions), 1)
            self.assertEqual(positions[0]['instrument'], 'EUR_USD')
            self.assertEqual(positions[0]['units'], 1000.0)
            self.assertEqual(positions[0]['unrealized_pl'], 15.50)
            self.assertEqual(positions[0]['entry_price'], 1.1000)
            self.assertEqual(positions[0]['direction'], 'BUY')
    
    def test_get_open_positions_handles_short_positions(self):
        """Test getting short positions correctly."""
        # Mock API response for short position
        mock_response = {
            'positions': [
                {
                    'instrument': 'USD_JPY',
                    'long': {
                        'units': '0',
                        'unrealizedPL': '0',
                        'averagePrice': '0'
                    },
                    'short': {
                        'units': '-2000',
                        'unrealizedPL': '20.00',
                        'averagePrice': '150.50'
                    }
                }
            ]
        }
        
        with patch.object(self.bot, '_rate_limited_request', return_value=mock_response):
            positions = self.bot.get_open_positions_with_details()
            
            self.assertEqual(len(positions), 1)
            self.assertEqual(positions[0]['instrument'], 'USD_JPY')
            self.assertEqual(positions[0]['units'], -2000.0)
            self.assertEqual(positions[0]['unrealized_pl'], 20.00)
            self.assertEqual(positions[0]['entry_price'], 150.50)
            self.assertEqual(positions[0]['direction'], 'SELL')
    
    def test_should_close_position_at_profit_when_target_reached(self):
        """Test position closure decision when profit target is reached."""
        # Create a position with profit above target
        position = {
            'instrument': 'EUR_USD',
            'units': 1000,
            'unrealized_pl': 15.00,  # $15 profit
            'entry_price': 1.1000
        }
        
        # Mock pip value calculation
        with patch.object(self.bot, '_calculate_pip_value', return_value=0.0001):
            # Target is 10 pips, we have profit of 15 pips
            # profit_pips = 15.00 / (1000 * 0.0001) = 15.00 / 0.1 = 150 pips
            # Wait, that doesn't match. Let me recalculate...
            # For EUR/USD, 1 pip = $0.0001 per unit
            # 1000 units * 0.0001 = $0.10 per pip
            # $15 profit / $0.10 per pip = 150 pips profit
            
            should_close, reason, profit_pips = self.bot.should_close_position_at_profit(
                position, take_profit_pips=10.0
            )
            
            self.assertTrue(should_close)
            self.assertIn("Profit target reached", reason)
            self.assertGreater(profit_pips, 10.0)
    
    def test_should_not_close_position_when_target_not_reached(self):
        """Test position is not closed when profit target is not reached."""
        position = {
            'instrument': 'EUR_USD',
            'units': 1000,
            'unrealized_pl': 0.50,  # Only $0.50 profit
            'entry_price': 1.1000
        }
        
        # Mock pip value calculation
        with patch.object(self.bot, '_calculate_pip_value', return_value=0.0001):
            # profit_pips = 0.50 / (1000 * 0.0001) = 5 pips profit
            
            should_close, reason, profit_pips = self.bot.should_close_position_at_profit(
                position, take_profit_pips=10.0
            )
            
            self.assertFalse(should_close)
            self.assertIn("below target", reason)
            self.assertLess(profit_pips, 10.0)
    
    def test_should_handle_negative_profit(self):
        """Test position with negative profit (loss) is not closed."""
        position = {
            'instrument': 'EUR_USD',
            'units': 1000,
            'unrealized_pl': -5.00,  # $5 loss
            'entry_price': 1.1000
        }
        
        # Mock pip value calculation
        with patch.object(self.bot, '_calculate_pip_value', return_value=0.0001):
            should_close, reason, profit_pips = self.bot.should_close_position_at_profit(
                position, take_profit_pips=10.0
            )
            
            self.assertFalse(should_close)
            self.assertLess(profit_pips, 0)  # Negative profit
    
    def test_close_position_success(self):
        """Test closing a position successfully."""
        instrument = 'EUR_USD'
        
        # Mock position details response
        mock_position_details = {
            'position': {
                'long': {'units': '1000'},
                'short': {'units': '0'}
            }
        }
        
        # Mock position close response
        mock_close_response = {
            'longOrderFillTransaction': {
                'id': '12345',
                'units': '-1000',
                'pl': '15.00'
            }
        }
        
        with patch.object(self.bot, '_rate_limited_request') as mock_request:
            mock_request.side_effect = [mock_position_details, mock_close_response]
            
            result = self.bot.close_position(instrument)
            
            self.assertTrue(result)
            self.assertEqual(mock_request.call_count, 2)
    
    def test_close_position_handles_short_position(self):
        """Test closing a short position."""
        instrument = 'USD_JPY'
        
        # Mock position details for short position
        mock_position_details = {
            'position': {
                'long': {'units': '0'},
                'short': {'units': '-2000'}
            }
        }
        
        mock_close_response = {
            'shortOrderFillTransaction': {
                'id': '12345',
                'units': '2000',
                'pl': '20.00'
            }
        }
        
        with patch.object(self.bot, '_rate_limited_request') as mock_request:
            mock_request.side_effect = [mock_position_details, mock_close_response]
            
            result = self.bot.close_position(instrument)
            
            self.assertTrue(result)
    
    def test_close_position_handles_errors(self):
        """Test error handling when closing position fails."""
        instrument = 'EUR_USD'
        
        with patch.object(self.bot, '_rate_limited_request', side_effect=Exception("API Error")):
            result = self.bot.close_position(instrument)
            
            self.assertFalse(result)
    
    def test_monitor_positions_processes_open_positions(self):
        """Test monitoring loop processes open positions correctly."""
        # Insert test trade
        self._insert_test_trade('EUR_USD', take_profit_pips=10.0)
        
        # Mock open positions with profit above target
        mock_positions = [{
            'instrument': 'EUR_USD',
            'units': 1000,
            'unrealized_pl': 15.00,
            'entry_price': 1.1000,
            'direction': 'BUY'
        }]
        
        # Create a flag to track if we've run once
        call_count = [0]
        
        def mock_get_positions():
            call_count[0] += 1
            # Return positions on first call, then set stop event
            if call_count[0] == 1:
                return mock_positions
            else:
                self.bot.position_monitor_stop_event.set()
                return []
        
        # Mock methods
        with patch.object(self.bot, 'get_open_positions_with_details', side_effect=mock_get_positions):
            with patch.object(self.bot, 'should_close_position_at_profit', return_value=(True, "Target reached", 150.0)):
                with patch.object(self.bot, 'close_position', return_value=True):
                    # Run monitoring (will exit after processing one position)
                    self.bot.monitor_positions_for_take_profit()
                    
                    # Verify position was closed in database
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT status FROM trades WHERE instrument = 'EUR_USD'")
                    result = cursor.fetchone()
                    conn.close()
                    
                    self.assertEqual(result[0], 'CLOSED_TP_MONITOR')
    
    def test_start_position_monitoring_creates_thread(self):
        """Test that starting monitoring creates a thread."""
        # Ensure monitoring is enabled
        self.bot.enable_position_monitoring = True
        
        # Start monitoring
        self.bot.start_position_monitoring()
        
        # Check thread was created and started
        self.assertIsNotNone(self.bot.position_monitor_thread)
        self.assertTrue(self.bot.position_monitor_thread.is_alive())
        
        # Clean up
        self.bot.stop_position_monitoring()
    
    def test_start_position_monitoring_respects_disabled_flag(self):
        """Test that monitoring doesn't start when disabled."""
        # Disable monitoring
        self.bot.enable_position_monitoring = False
        
        # Try to start monitoring
        self.bot.start_position_monitoring()
        
        # Thread should not be created
        self.assertIsNone(self.bot.position_monitor_thread)
    
    def test_stop_position_monitoring_stops_thread(self):
        """Test that stopping monitoring stops the thread."""
        # Mock API to return empty positions to avoid errors
        with patch.object(self.bot, 'get_open_positions_with_details', return_value=[]):
            # Enable and start monitoring
            self.bot.enable_position_monitoring = True
            self.bot.start_position_monitoring()
            
            # Verify thread is running
            self.assertTrue(self.bot.position_monitor_thread.is_alive())
            
            # Stop monitoring
            self.bot.stop_position_monitoring()
            
            # Wait a moment for thread to stop
            time.sleep(0.5)
            
            # Verify thread is None after stop
            self.assertIsNone(self.bot.position_monitor_thread)
    
    def test_monitoring_handles_empty_positions(self):
        """Test monitoring handles empty position list gracefully."""
        # Mock empty positions
        with patch.object(self.bot, 'get_open_positions_with_details', return_value=[]):
            # Set stop event to exit after one iteration
            self.bot.position_monitor_stop_event.set()
            
            # This should not raise any exceptions
            try:
                self.bot.monitor_positions_for_take_profit()
            except Exception as e:
                self.fail(f"Monitoring raised exception with empty positions: {e}")
    
    def test_monitoring_handles_missing_trade_record(self):
        """Test monitoring handles positions without database record."""
        # Mock open positions but don't insert trade record
        mock_positions = [{
            'instrument': 'EUR_USD',
            'units': 1000,
            'unrealized_pl': 15.00,
            'entry_price': 1.1000,
            'direction': 'BUY'
        }]
        
        with patch.object(self.bot, 'get_open_positions_with_details', return_value=mock_positions):
            # Set stop event to exit after one iteration
            self.bot.position_monitor_stop_event.set()
            
            # This should not raise exceptions, just skip the position
            try:
                self.bot.monitor_positions_for_take_profit()
            except Exception as e:
                self.fail(f"Monitoring raised exception with missing trade record: {e}")


class TestPositionMonitoringIntegration(unittest.TestCase):
    """Integration tests for position monitoring with bot lifecycle."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary database
        self.db_fd, self.db_path = tempfile.mkstemp()
        
        # Mock the bot
        with patch('bot.oandapyV20.API'), \
             patch('bot.TradeDatabase') as mock_db, \
             patch('bot.MLPredictor'), \
             patch('bot.PositionSizer'), \
             patch('bot.MultiTimeframeAnalyzer'), \
             patch('bot.AdaptiveThresholdManager'), \
             patch('bot.VolatilityDetector'), \
             patch('bot.DataValidator'), \
             patch('bot.RiskValidator'), \
             patch('bot.RiskManager'), \
             patch('bot.StructuredLogger'), \
             patch('bot.PerformanceMonitor'):
            
            mock_db.return_value.db_path = self.db_path
            
            from bot import OandaTradingBot
            
            with patch.object(OandaTradingBot, 'get_balance', return_value=10000.0):
                with patch.object(OandaTradingBot, '_fetch_and_cache_instruments'):
                    self.bot = OandaTradingBot(
                        enable_ml=False,
                        enable_multiframe=False,
                        enable_adaptive_threshold=False,
                        enable_volatility_detection=False
                    )
                    self.bot.db.db_path = self.db_path
    
    def tearDown(self):
        """Clean up test fixtures."""
        if hasattr(self.bot, 'position_monitor_thread') and self.bot.position_monitor_thread:
            self.bot.stop_position_monitoring()
        
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_run_method_starts_and_stops_monitoring(self):
        """Test that bot.run() starts and stops monitoring thread."""
        # Mock run_cycle to return False immediately (stop after one cycle)
        with patch.object(self.bot, 'run_cycle', return_value=False):
            # Run the bot (will exit immediately due to mock)
            self.bot.run()
            
            # Thread should have been started and then stopped
            # Since run() has exited, thread should be None or stopped
            if self.bot.position_monitor_thread:
                self.assertFalse(self.bot.position_monitor_thread.is_alive())


if __name__ == '__main__':
    unittest.main()
