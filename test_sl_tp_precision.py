"""
Unit tests for SL/TP distance precision rounding.
Tests that stop loss and take profit distances are rounded to appropriate
decimal places based on instrument type to comply with Oanda API requirements.
"""
import unittest
from unittest.mock import patch
from bot import OandaTradingBot


class TestSLTPPrecisionRounding(unittest.TestCase):
    """Test that SL/TP distances are rounded correctly for different instruments."""
    
    def setUp(self):
        """Set up test bot instance with mocked API."""
        with patch('bot.oandapyV20.API'):
            with patch.object(OandaTradingBot, '_rate_limited_request') as mock_request:
                # Mock the account summary response for balance
                mock_request.return_value = {
                    'account': {'balance': '10000.0'}
                }
                
                # Mock instruments cache with different instrument types
                mock_instruments_response = {
                    'instruments': [
                        {
                            'name': 'EUR_USD',
                            'pipLocation': -4,
                            'displayName': 'EUR/USD',
                            'type': 'CURRENCY',
                            'displayPrecision': 5,
                            'tradeUnitsPrecision': 0
                        },
                        {
                            'name': 'USD_JPY',
                            'pipLocation': -2,
                            'displayName': 'USD/JPY',
                            'type': 'CURRENCY',
                            'displayPrecision': 3,
                            'tradeUnitsPrecision': 0
                        },
                        {
                            'name': 'GBP_USD',
                            'pipLocation': -4,
                            'displayName': 'GBP/USD',
                            'type': 'CURRENCY',
                            'displayPrecision': 5,
                            'tradeUnitsPrecision': 0
                        },
                        {
                            'name': 'XAU_USD',  # Gold
                            'pipLocation': -2,
                            'displayName': 'Gold',
                            'type': 'METAL',
                            'displayPrecision': 2,
                            'tradeUnitsPrecision': 0
                        }
                    ]
                }
                
                def mock_rate_limited_side_effect(self, endpoint):
                    if 'AccountInstruments' in str(type(endpoint)):
                        return mock_instruments_response
                    return {'account': {'balance': '10000.0'}}
                
                with patch.object(OandaTradingBot, '_rate_limited_request', mock_rate_limited_side_effect):
                    self.bot = OandaTradingBot(
                        enable_ml=False,
                        enable_multiframe=False,
                        enable_adaptive_threshold=False,
                        enable_volatility_detection=False
                    )
    
    def test_round_sl_tp_distance_eur_usd(self):
        """Test SL/TP rounding for EUR_USD (pipLocation=-4, displayPrecision=5)."""
        instrument = 'EUR_USD'
        
        # Test with high precision input (e.g., 10.123456789 pips)
        distance_pips = 10.123456789
        rounded = self.bot._round_sl_tp_distance(distance_pips, instrument)
        
        # EUR_USD has pipLocation=-4, so pip_size=0.0001
        # distance = 10.123456789 * 0.0001 = 0.0010123456789
        # With displayPrecision=5, should round to 0.00101
        self.assertEqual(rounded, '0.00101')
        
        # Test with another value
        distance_pips = 25.987654321
        rounded = self.bot._round_sl_tp_distance(distance_pips, instrument)
        # distance = 25.987654321 * 0.0001 = 0.0025987654321
        # With displayPrecision=5, should round to 0.00260
        self.assertEqual(rounded, '0.00260')
    
    def test_round_sl_tp_distance_usd_jpy(self):
        """Test SL/TP rounding for USD_JPY (pipLocation=-2, displayPrecision=3)."""
        instrument = 'USD_JPY'
        
        # Test with high precision input (e.g., 20.123456789 pips)
        distance_pips = 20.123456789
        rounded = self.bot._round_sl_tp_distance(distance_pips, instrument)
        
        # USD_JPY has pipLocation=-2, so pip_size=0.01
        # distance = 20.123456789 * 0.01 = 0.20123456789
        # With displayPrecision=3, should round to 0.201
        self.assertEqual(rounded, '0.201')
        
        # Test with another value
        distance_pips = 15.678
        rounded = self.bot._round_sl_tp_distance(distance_pips, instrument)
        # distance = 15.678 * 0.01 = 0.15678
        # With displayPrecision=3, should round to 0.157
        self.assertEqual(rounded, '0.157')
    
    def test_round_sl_tp_distance_gbp_usd(self):
        """Test SL/TP rounding for GBP_USD (pipLocation=-4, displayPrecision=5)."""
        instrument = 'GBP_USD'
        
        # Test with high precision input
        distance_pips = 8.555555555
        rounded = self.bot._round_sl_tp_distance(distance_pips, instrument)
        
        # GBP_USD has pipLocation=-4, so pip_size=0.0001
        # distance = 8.555555555 * 0.0001 = 0.0008555555555
        # With displayPrecision=5, should round to 0.00086
        self.assertEqual(rounded, '0.00086')
    
    def test_round_sl_tp_distance_gold(self):
        """Test SL/TP rounding for XAU_USD/Gold (pipLocation=-2, displayPrecision=2)."""
        instrument = 'XAU_USD'
        
        # Test with high precision input
        distance_pips = 5.123456789
        rounded = self.bot._round_sl_tp_distance(distance_pips, instrument)
        
        # XAU_USD has pipLocation=-2, so pip_size=0.01
        # distance = 5.123456789 * 0.01 = 0.05123456789
        # With displayPrecision=2, should round to 0.05
        self.assertEqual(rounded, '0.05')
        
        # Test with another value that needs rounding
        distance_pips = 10.888
        rounded = self.bot._round_sl_tp_distance(distance_pips, instrument)
        # distance = 10.888 * 0.01 = 0.10888
        # With displayPrecision=2, should round to 0.11
        self.assertEqual(rounded, '0.11')
    
    def test_round_sl_tp_distance_small_values(self):
        """Test SL/TP rounding for small distance values."""
        instrument = 'EUR_USD'
        
        # Test with very small distance (e.g., 1 pip)
        distance_pips = 1.0
        rounded = self.bot._round_sl_tp_distance(distance_pips, instrument)
        # distance = 1.0 * 0.0001 = 0.0001
        self.assertEqual(rounded, '0.00010')
        
        # Test with fractional pip
        distance_pips = 0.5
        rounded = self.bot._round_sl_tp_distance(distance_pips, instrument)
        # distance = 0.5 * 0.0001 = 0.00005
        self.assertEqual(rounded, '0.00005')
    
    def test_round_sl_tp_distance_large_values(self):
        """Test SL/TP rounding for large distance values."""
        instrument = 'EUR_USD'
        
        # Test with large distance (e.g., 100 pips)
        distance_pips = 100.0
        rounded = self.bot._round_sl_tp_distance(distance_pips, instrument)
        # distance = 100.0 * 0.0001 = 0.01
        self.assertEqual(rounded, '0.01000')
        
        # Test with large distance with decimals
        distance_pips = 150.7654321
        rounded = self.bot._round_sl_tp_distance(distance_pips, instrument)
        # distance = 150.7654321 * 0.0001 = 0.01507654321
        # With displayPrecision=5, should round to 0.01508
        self.assertEqual(rounded, '0.01508')
    
    def test_round_sl_tp_distance_unknown_instrument(self):
        """Test SL/TP rounding for unknown instrument (fallback behavior)."""
        instrument = 'UNKNOWN_PAIR'
        
        # For unknown instrument, should use legacy logic
        # Non-JPY pairs default to pip_size=0.0001, displayPrecision=5
        distance_pips = 10.123456789
        rounded = self.bot._round_sl_tp_distance(distance_pips, instrument)
        
        # Should fall back to default precision handling
        # pip_size = 0.0001 (default for non-JPY)
        # distance = 10.123456789 * 0.0001 = 0.0010123456789
        # With displayPrecision=5, should round to 0.00101
        self.assertEqual(rounded, '0.00101')
    
    def test_round_sl_tp_distance_preserves_format(self):
        """Test that rounding preserves string format with proper decimal places."""
        instrument = 'EUR_USD'
        
        # Test that result is properly formatted string with no trailing spaces
        distance_pips = 10.0
        rounded = self.bot._round_sl_tp_distance(distance_pips, instrument)
        
        # Should be properly formatted as string
        self.assertIsInstance(rounded, str)
        self.assertEqual(rounded, '0.00100')
        
        # Should not have scientific notation
        distance_pips = 0.0001
        rounded = self.bot._round_sl_tp_distance(distance_pips, instrument)
        self.assertNotIn('e', rounded.lower())  # No scientific notation


class TestPlaceOrderWithPrecision(unittest.TestCase):
    """Test that place_order uses precision rounding for SL/TP."""
    
    def setUp(self):
        """Set up test bot instance with mocked API."""
        with patch('bot.oandapyV20.API'):
            with patch.object(OandaTradingBot, '_rate_limited_request') as mock_request:
                mock_instruments_response = {
                    'instruments': [
                        {
                            'name': 'EUR_USD',
                            'pipLocation': -4,
                            'displayName': 'EUR/USD',
                            'type': 'CURRENCY',
                            'displayPrecision': 5,
                            'tradeUnitsPrecision': 0
                        }
                    ]
                }
                
                def mock_rate_limited_side_effect(self, endpoint):
                    if 'AccountInstruments' in str(type(endpoint)):
                        return mock_instruments_response
                    return {'account': {'balance': '10000.0'}}
                
                with patch.object(OandaTradingBot, '_rate_limited_request', mock_rate_limited_side_effect):
                    self.bot = OandaTradingBot(
                        enable_ml=False,
                        enable_multiframe=False,
                        enable_adaptive_threshold=False,
                        enable_volatility_detection=False
                    )
    
    @patch('bot.orders.OrderCreate')
    def test_place_order_uses_rounded_sl_tp(self, mock_order_create):
        """Test that place_order rounds SL/TP distances properly."""
        instrument = 'EUR_USD'
        side = 'BUY'
        units = 1000
        sl_pips = 10.123456789  # High precision input
        tp_pips = 20.987654321  # High precision input
        
        # Mock the order creation and API request
        with patch.object(self.bot, '_rate_limited_request') as mock_request:
            # Mock both margin check and order creation responses
            def mock_request_side_effect(endpoint):
                endpoint_type = str(type(endpoint))
                if 'AccountSummary' in endpoint_type:
                    return {
                        'account': {
                            'balance': '10000.0',
                            'marginAvailable': '9000.0'
                        }
                    }
                else:
                    return {
                        'orderFillTransaction': {
                            'id': '123',
                            'units': '1000',
                            'price': '1.1000'
                        }
                    }
            
            mock_request.side_effect = mock_request_side_effect
            
            # Call place_order
            self.bot.place_order(instrument, side, units, sl_pips, tp_pips, current_price=1.1000)
            
            # Verify OrderCreate was called
            self.assertTrue(mock_order_create.called)
            
            # Get the data passed to OrderCreate
            call_args = mock_order_create.call_args
            order_data = call_args[1]['data']
            
            # Check that SL and TP distances are properly rounded strings
            sl_distance = order_data['order']['stopLossOnFill']['distance']
            tp_distance = order_data['order']['takeProfitOnFill']['distance']
            
            # Verify they are strings
            self.assertIsInstance(sl_distance, str)
            self.assertIsInstance(tp_distance, str)
            
            # Verify proper rounding was applied
            # sl_pips = 10.123456789 * 0.0001 = 0.0010123456789 -> rounded to 0.00101
            self.assertEqual(sl_distance, '0.00101')
            # tp_pips = 20.987654321 * 0.0001 = 0.0020987654321 -> rounded to 0.00210
            self.assertEqual(tp_distance, '0.00210')


if __name__ == '__main__':
    unittest.main()
