"""
Test curated instruments filter functionality.
"""
import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot import OandaTradingBot
import config


class TestCuratedFilter(unittest.TestCase):
    """Test curated instruments filter for FX majors."""
    
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
                    'balance': '1000.00',
                    'marginAvailable': '500.00'
                }
            }
            
            # Create bot with minimal features enabled
            self.bot = OandaTradingBot(
                enable_ml=False,
                enable_multiframe=False,
                enable_adaptive_threshold=False,
                enable_volatility_detection=False
            )
    
    def test_filter_with_overlap(self):
        """Test that filter returns curated intersection when overlap exists."""
        # Test with a mix of curated and non-curated instruments
        test_pairs = [
            'EUR_USD',  # Curated
            'GBP_USD',  # Curated
            'XAU_USD',  # Not curated (gold)
            'USD_JPY',  # Curated
            'BCO_USD',  # Not curated (oil)
            'AUD_USD',  # Curated
        ]
        
        # Expected: Only curated FX majors
        expected = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD']
        
        # Apply filter
        with patch('bot.ENABLE_CURATED_FILTER', True):
            filtered = self.bot._apply_curated_filter(test_pairs)
        
        # Verify
        self.assertEqual(filtered, expected)
        self.assertEqual(len(filtered), 4)
    
    def test_filter_without_overlap_is_noop(self):
        """Test that filter returns original list when no overlap (test-safe no-op)."""
        # Test with synthetic/test symbols that don't match curated list
        test_pairs = ['TEST_SYMBOL1', 'TEST_SYMBOL2', 'SYNTHETIC_PAIR']
        
        # Apply filter
        with patch('bot.ENABLE_CURATED_FILTER', True):
            filtered = self.bot._apply_curated_filter(test_pairs)
        
        # Verify: Should return original list unchanged (no-op)
        self.assertEqual(filtered, test_pairs)
        self.assertEqual(len(filtered), 3)
    
    def test_filter_disabled(self):
        """Test that filter is a no-op when disabled."""
        test_pairs = ['EUR_USD', 'XAU_USD', 'GBP_USD', 'BCO_USD']
        
        # Apply filter with disabled flag
        with patch('bot.ENABLE_CURATED_FILTER', False):
            filtered = self.bot._apply_curated_filter(test_pairs)
        
        # Verify: Should return original list unchanged
        self.assertEqual(filtered, test_pairs)
        self.assertEqual(len(filtered), 4)
    
    def test_filter_preserves_order(self):
        """Test that filter preserves the original order of instruments."""
        # Test with curated instruments in specific order
        test_pairs = ['USD_JPY', 'EUR_USD', 'AUD_USD', 'GBP_USD']
        
        # Apply filter
        with patch('bot.ENABLE_CURATED_FILTER', True):
            filtered = self.bot._apply_curated_filter(test_pairs)
        
        # Verify: Order should be preserved
        self.assertEqual(filtered, test_pairs)
    
    def test_filter_with_all_curated(self):
        """Test filter when all instruments are already curated."""
        # All curated FX majors
        test_pairs = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'USD_CAD']
        
        # Apply filter
        with patch('bot.ENABLE_CURATED_FILTER', True):
            filtered = self.bot._apply_curated_filter(test_pairs)
        
        # Verify: All should pass through
        self.assertEqual(filtered, test_pairs)
        self.assertEqual(len(filtered), 4)
    
    def test_filter_with_empty_list(self):
        """Test filter with empty input list."""
        test_pairs = []
        
        # Apply filter
        with patch('bot.ENABLE_CURATED_FILTER', True):
            filtered = self.bot._apply_curated_filter(test_pairs)
        
        # Verify: Empty list should remain empty
        self.assertEqual(filtered, [])
    
    def test_curated_instruments_config(self):
        """Test that CURATED_INSTRUMENTS config is properly set."""
        # Verify the config has the expected FX majors
        expected_majors = ["EUR_USD", "GBP_USD", "USD_JPY", "USD_CAD", 
                          "AUD_USD", "NZD_USD", "EUR_GBP", "USD_CHF"]
        
        self.assertEqual(config.CURATED_INSTRUMENTS, expected_majors)
        self.assertTrue(config.ENABLE_CURATED_FILTER)


if __name__ == '__main__':
    unittest.main()
