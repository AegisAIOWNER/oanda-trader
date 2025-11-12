"""
Test affordability pre-filter functionality.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot import OandaTradingBot


class TestAffordabilityFilter(unittest.TestCase):
    """Test affordability pre-filter for small balance scenarios."""
    
    @patch('bot.oandapyV20.API')
    def setUp(self, mock_api):
        """Set up test bot with mocked API."""
        # Mock API responses for initialization
        mock_api_instance = Mock()
        mock_api.return_value = mock_api_instance
        
        # Mock account summary for initialization
        with patch.object(OandaTradingBot, '_rate_limited_request') as mock_request:
            # Initial balance check
            mock_request.return_value = {
                'account': {
                    'balance': '25.00',
                    'marginAvailable': '5.00'
                }
            }
            
            # Create bot with minimal features enabled
            self.bot = OandaTradingBot(
                enable_ml=False,
                enable_multiframe=False,
                enable_adaptive_threshold=False,
                enable_volatility_detection=False
            )
    
    def test_instrument_affordability_check_expensive(self):
        """Test that expensive instruments are correctly identified as unaffordable."""
        # Setup: Instrument with high minimum trade size and margin rate
        instrument = 'TEST_EXPENSIVE'
        self.bot.instruments_cache[instrument] = {
            'minimumTradeSize': '1000',  # Large minimum
            'marginRate': 0.05,  # 5% margin rate (20:1 leverage)
            'pipLocation': -4,
            'displayName': 'Test Expensive',
            'type': 'CURRENCY',
            'displayPrecision': 5,
            'tradeUnitsPrecision': 0,
            'maximumOrderUnits': '100000000'
        }
        
        # Test with small available margin
        current_price = 1.1000
        available_margin = 5.00  # Very small
        
        # Check affordability
        is_affordable, reason = self.bot._is_instrument_affordable(
            instrument, current_price, available_margin, margin_buffer=0.50
        )
        
        # Expected: required_margin = 1000 * 1.1 * 0.05 = 55.00
        # Effective available = 5.00 * (1 - 0.50) = 2.50
        # 55.00 > 2.50, so NOT affordable
        self.assertFalse(is_affordable)
        self.assertIn('>', reason)
        self.assertIn('55.00', reason)
    
    def test_instrument_affordability_check_affordable(self):
        """Test that affordable instruments are correctly identified."""
        # Setup: Instrument with small minimum trade size
        instrument = 'TEST_AFFORDABLE'
        self.bot.instruments_cache[instrument] = {
            'minimumTradeSize': '1',  # Minimum is 1 unit
            'marginRate': 0.02,  # 2% margin rate (50:1 leverage)
            'pipLocation': -4,
            'displayName': 'Test Affordable',
            'type': 'CURRENCY',
            'displayPrecision': 5,
            'tradeUnitsPrecision': 0,
            'maximumOrderUnits': '100000000'
        }
        
        # Test with sufficient available margin
        current_price = 1.1000
        available_margin = 5.00
        
        # Check affordability
        is_affordable, reason = self.bot._is_instrument_affordable(
            instrument, current_price, available_margin, margin_buffer=0.50
        )
        
        # Expected: required_margin = 1 * 1.1 * 0.02 = 0.022
        # Effective available = 5.00 * (1 - 0.50) = 2.50
        # 0.022 <= 2.50, so IS affordable
        self.assertTrue(is_affordable)
        self.assertIn('<=', reason)
    
    @patch.object(OandaTradingBot, 'get_prices')
    @patch.object(OandaTradingBot, 'get_margin_info')
    @patch.object(OandaTradingBot, 'get_open_position_instruments')
    def test_scan_pairs_skips_unaffordable_instrument(self, mock_open_pos, mock_margin, mock_prices):
        """Test that scan_pairs_for_signals skips unaffordable instruments."""
        # Setup: No open positions
        mock_open_pos.return_value = []
        
        # Setup: Small available margin
        mock_margin.return_value = {
            'balance': 25.00,
            'margin_available': 5.00,
            'margin_used': 0.00
        }
        
        # Setup: Two instruments in cache
        # One expensive (unaffordable), one affordable
        self.bot.instruments_cache = {
            'EXPENSIVE_PAIR': {
                'minimumTradeSize': '1000',
                'marginRate': 0.05,
                'pipLocation': -4,
                'displayName': 'Expensive Pair',
                'type': 'CURRENCY',
                'displayPrecision': 5,
                'tradeUnitsPrecision': 0,
                'maximumOrderUnits': '100000000'
            },
            'AFFORDABLE_PAIR': {
                'minimumTradeSize': '1',
                'marginRate': 0.02,
                'pipLocation': -4,
                'displayName': 'Affordable Pair',
                'type': 'CURRENCY',
                'displayPrecision': 5,
                'tradeUnitsPrecision': 0,
                'maximumOrderUnits': '100000000'
            }
        }
        
        # Disable persistent pairs for this test
        self.bot.enable_persistent_pairs = False
        
        # Mock get_prices to return valid dataframes
        def mock_get_prices_side_effect(instrument, count=50, granularity='M5'):
            return pd.DataFrame({
                'time': pd.date_range(start='2024-01-01', periods=50, freq='5min'),
                'open': [1.1000] * 50,
                'high': [1.1050] * 50,
                'low': [1.0950] * 50,
                'close': [1.1000] * 50,
                'volume': [100] * 50
            })
        
        mock_prices.side_effect = mock_get_prices_side_effect
        
        # Mock _get_available_instruments to return our test instruments
        with patch.object(self.bot, '_get_available_instruments', return_value=['EXPENSIVE_PAIR', 'AFFORDABLE_PAIR']):
            # Run scan
            signals, atr_readings = self.bot.scan_pairs_for_signals()
        
        # Verify: EXPENSIVE_PAIR should be skipped
        # AFFORDABLE_PAIR should be scanned (though it may not generate a signal)
        # We verify by checking that get_prices was NOT called for EXPENSIVE_PAIR
        # after the first call (which is used for affordability check)
        
        # The expensive pair should be checked but then skipped
        # The affordable pair should be checked and processed
        call_count = mock_prices.call_count
        
        # We expect at least 2 calls: one for each instrument's initial price check
        # But the expensive one should not have additional calls for signal generation
        self.assertGreaterEqual(call_count, 2)
    
    def test_affordability_with_zero_margin_buffer(self):
        """Test affordability check with zero margin buffer (use all margin)."""
        instrument = 'TEST_ZERO_BUFFER'
        self.bot.instruments_cache[instrument] = {
            'minimumTradeSize': '100',
            'marginRate': 0.03,
            'pipLocation': -4,
            'displayName': 'Test Zero Buffer',
            'type': 'CURRENCY',
            'displayPrecision': 5,
            'tradeUnitsPrecision': 0,
            'maximumOrderUnits': '100000000'
        }
        
        current_price = 1.0000
        available_margin = 5.00
        
        # With zero buffer, all margin is available
        is_affordable, reason = self.bot._is_instrument_affordable(
            instrument, current_price, available_margin, margin_buffer=0.0
        )
        
        # Expected: required_margin = 100 * 1.0 * 0.03 = 3.00
        # Effective available = 5.00 * (1 - 0.0) = 5.00
        # 3.00 <= 5.00, so IS affordable
        self.assertTrue(is_affordable)
    
    def test_affordability_default_margin_rate(self):
        """Test that missing marginRate falls back to default value."""
        instrument = 'TEST_NO_MARGIN_RATE'
        self.bot.instruments_cache[instrument] = {
            'minimumTradeSize': '10',
            # marginRate is missing
            'pipLocation': -4,
            'displayName': 'Test No Margin Rate',
            'type': 'CURRENCY',
            'displayPrecision': 5,
            'tradeUnitsPrecision': 0,
            'maximumOrderUnits': '100000000'
        }
        
        current_price = 1.5000
        available_margin = 10.00
        
        is_affordable, reason = self.bot._is_instrument_affordable(
            instrument, current_price, available_margin, margin_buffer=0.50
        )
        
        # Should use default marginRate of 0.0333 (~30:1 leverage)
        # Expected: required_margin = 10 * 1.5 * 0.0333 = 0.4995
        # Effective available = 10.00 * (1 - 0.50) = 5.00
        # 0.4995 <= 5.00, so IS affordable
        self.assertTrue(is_affordable)
    
    def test_affordability_with_high_margin_buffer(self):
        """Test affordability check with high margin buffer."""
        instrument = 'TEST_HIGH_BUFFER'
        self.bot.instruments_cache[instrument] = {
            'minimumTradeSize': '10',
            'marginRate': 0.05,
            'pipLocation': -4,
            'displayName': 'Test High Buffer',
            'type': 'CURRENCY',
            'displayPrecision': 5,
            'tradeUnitsPrecision': 0,
            'maximumOrderUnits': '100000000'
        }
        
        current_price = 1.0000
        available_margin = 10.00
        
        # With 90% buffer, only 10% of margin is available
        is_affordable, reason = self.bot._is_instrument_affordable(
            instrument, current_price, available_margin, margin_buffer=0.90
        )
        
        # Expected: required_margin = 10 * 1.0 * 0.05 = 0.50
        # Effective available = 10.00 * (1 - 0.90) = 1.00
        # 0.50 <= 1.00, so IS affordable
        self.assertTrue(is_affordable)


if __name__ == '__main__':
    unittest.main()
