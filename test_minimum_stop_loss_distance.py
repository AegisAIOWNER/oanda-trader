"""
Unit tests for minimum stop loss distance validation.
Tests that stop loss distances are adjusted to meet Oanda's minimum trailing
stop distance requirements to prevent STOP_LOSS_ON_FILL_LOSS errors.
"""
import unittest
from unittest.mock import patch, MagicMock
from bot import OandaTradingBot


class TestMinimumStopLossDistance(unittest.TestCase):
    """Test that SL distances meet minimum trailing stop distance requirements."""
    
    def setUp(self):
        """Set up test bot instance with mocked API."""
        with patch('bot.oandapyV20.API'):
            with patch.object(OandaTradingBot, '_rate_limited_request') as mock_request:
                # Mock the account summary response for balance
                mock_request.return_value = {
                    'account': {'balance': '10000.0', 'marginAvailable': '5000.0'}
                }
                
                # Create bot instance with caching disabled to control test data
                self.bot = OandaTradingBot(
                    enable_ml=False,
                    enable_multiframe=False,
                    enable_adaptive_threshold=False,
                    enable_volatility_detection=False
                )
                
                # Manually set up instruments cache with known values
                self.bot.instruments_cache = {
                    'EUR_USD': {
                        'pipLocation': -4,
                        'displayName': 'EUR/USD',
                        'type': 'CURRENCY',
                        'displayPrecision': 5,
                        'tradeUnitsPrecision': 0,
                        'minimumTradeSize': '1',
                        'maximumOrderUnits': '100000000',
                        'marginRate': 0.0333,
                        'minimumTrailingStopDistance': '0.001'
                    },
                    'USD_JPY': {
                        'pipLocation': -2,
                        'displayName': 'USD/JPY',
                        'type': 'CURRENCY',
                        'displayPrecision': 3,
                        'tradeUnitsPrecision': 0,
                        'minimumTradeSize': '1',
                        'maximumOrderUnits': '100000000',
                        'marginRate': 0.0333,
                        'minimumTrailingStopDistance': '0.01'
                    },
                    'XAU_USD': {
                        'pipLocation': -2,
                        'displayName': 'Gold',
                        'type': 'METAL',
                        'displayPrecision': 3,
                        'tradeUnitsPrecision': 0,
                        'minimumTradeSize': '1',
                        'maximumOrderUnits': '10000',
                        'marginRate': 0.05,
                        'minimumTrailingStopDistance': '0.05'
                    }
                }
    
    def test_instruments_cache_includes_minimum_trailing_stop_distance(self):
        """Test that instruments cache includes minimumTrailingStopDistance field."""
        for instrument, data in self.bot.instruments_cache.items():
            self.assertIn('minimumTrailingStopDistance', data,
                         f"Instrument {instrument} missing minimumTrailingStopDistance")
            self.assertIsNotNone(data['minimumTrailingStopDistance'],
                               f"Instrument {instrument} has None minimumTrailingStopDistance")
    
    def test_stop_loss_adjustment_for_eur_usd_below_minimum(self):
        """Test that stop loss is adjusted when below minimum for EUR_USD."""
        instrument = 'EUR_USD'
        
        # EUR_USD has pip size 0.0001, minimum trailing stop distance 0.001
        # 0.001 / 0.0001 = 10 pips minimum
        # Test with 5 pips, which should be adjusted to 10 pips
        sl_pips = 5.0
        tp_pips = 20.0
        
        with patch.object(self.bot, '_rate_limited_request') as mock_request:
            with patch.object(self.bot, 'check_margin', return_value=True):
                with patch.object(self.bot, 'get_balance', return_value=10000.0):
                    with patch.object(self.bot.risk_manager, 'can_open_position', return_value=(True, '')):
                        # Mock the order creation to capture the data
                        def capture_order(endpoint):
                            # Store the data for inspection
                            self.order_data = endpoint.data
                            return {
                                'orderFillTransaction': {
                                    'id': '123',
                                    'units': '100',
                                    'price': '1.1000'
                                },
                                'orderCreateTransaction': {'id': '123'}
                            }
                        
                        mock_request.side_effect = capture_order
                        
                        # Place order with stop loss below minimum
                        self.bot.place_order(instrument, 'BUY', 100, sl_pips, tp_pips, 1.1000)
                        
                        # Check that stop loss was adjusted
                        self.assertIsNotNone(self.order_data)
                        sl_distance = float(self.order_data['order']['stopLossOnFill']['distance'])
                        
                        # The adjusted SL should be at least the minimum (0.001)
                        self.assertGreaterEqual(sl_distance, 0.001,
                                              f"SL distance {sl_distance} is below minimum 0.001")
    
    def test_stop_loss_no_adjustment_for_eur_usd_above_minimum(self):
        """Test that stop loss is NOT adjusted when already above minimum for EUR_USD."""
        instrument = 'EUR_USD'
        
        # EUR_USD has pip size 0.0001, minimum trailing stop distance 0.001
        # 0.001 / 0.0001 = 10 pips minimum
        # Test with 15 pips, which should NOT be adjusted
        sl_pips = 15.0
        tp_pips = 30.0
        
        with patch.object(self.bot, '_rate_limited_request') as mock_request:
            with patch.object(self.bot, 'check_margin', return_value=True):
                with patch.object(self.bot, 'get_balance', return_value=10000.0):
                    with patch.object(self.bot.risk_manager, 'can_open_position', return_value=(True, '')):
                        # Mock the order creation to capture the data
                        def capture_order(endpoint):
                            # Store the data for inspection
                            self.order_data = endpoint.data
                            return {
                                'orderFillTransaction': {
                                    'id': '123',
                                    'units': '100',
                                    'price': '1.1000'
                                },
                                'orderCreateTransaction': {'id': '123'}
                            }
                        
                        mock_request.side_effect = capture_order
                        
                        # Place order with stop loss above minimum
                        self.bot.place_order(instrument, 'BUY', 100, sl_pips, tp_pips, 1.1000)
                        
                        # Check that stop loss was not overly adjusted
                        self.assertIsNotNone(self.order_data)
                        sl_distance = float(self.order_data['order']['stopLossOnFill']['distance'])
                        
                        # The SL should be approximately 15 pips (0.0015) with rounding
                        expected_sl_distance = 15.0 * 0.0001  # 15 pips * pip size
                        self.assertAlmostEqual(sl_distance, expected_sl_distance, places=5,
                                             msg=f"SL distance {sl_distance} differs from expected {expected_sl_distance}")
    
    def test_stop_loss_adjustment_for_usd_jpy_below_minimum(self):
        """Test that stop loss is adjusted when below minimum for USD_JPY."""
        instrument = 'USD_JPY'
        
        # USD_JPY has pip size 0.01, minimum trailing stop distance 0.01
        # 0.01 / 0.01 = 1 pip minimum
        # Test with 0.5 pips, which should be adjusted to 1 pip
        sl_pips = 0.5
        tp_pips = 5.0
        
        with patch.object(self.bot, '_rate_limited_request') as mock_request:
            with patch.object(self.bot, 'check_margin', return_value=True):
                with patch.object(self.bot, 'get_balance', return_value=10000.0):
                    with patch.object(self.bot.risk_manager, 'can_open_position', return_value=(True, '')):
                        # Mock the order creation to capture the data
                        def capture_order(endpoint):
                            # Store the data for inspection
                            self.order_data = endpoint.data
                            return {
                                'orderFillTransaction': {
                                    'id': '123',
                                    'units': '100',
                                    'price': '110.00'
                                },
                                'orderCreateTransaction': {'id': '123'}
                            }
                        
                        mock_request.side_effect = capture_order
                        
                        # Place order with stop loss below minimum
                        self.bot.place_order(instrument, 'BUY', 100, sl_pips, tp_pips, 110.00)
                        
                        # Check that stop loss was adjusted
                        self.assertIsNotNone(self.order_data)
                        sl_distance = float(self.order_data['order']['stopLossOnFill']['distance'])
                        
                        # The adjusted SL should be at least the minimum (0.01)
                        self.assertGreaterEqual(sl_distance, 0.01,
                                              f"SL distance {sl_distance} is below minimum 0.01")
    
    def test_stop_loss_adjustment_for_gold_below_minimum(self):
        """Test that stop loss is adjusted when below minimum for XAU_USD (Gold)."""
        instrument = 'XAU_USD'
        
        # XAU_USD has pip size 0.01, minimum trailing stop distance 0.05
        # 0.05 / 0.01 = 5 pips minimum
        # Test with 2 pips, which should be adjusted to 5 pips
        sl_pips = 2.0
        tp_pips = 15.0
        
        with patch.object(self.bot, '_rate_limited_request') as mock_request:
            with patch.object(self.bot, 'check_margin', return_value=True):
                with patch.object(self.bot, 'get_balance', return_value=10000.0):
                    with patch.object(self.bot.risk_manager, 'can_open_position', return_value=(True, '')):
                        # Mock the order creation to capture the data
                        def capture_order(endpoint):
                            # Store the data for inspection
                            self.order_data = endpoint.data
                            return {
                                'orderFillTransaction': {
                                    'id': '123',
                                    'units': '10',
                                    'price': '1800.00'
                                },
                                'orderCreateTransaction': {'id': '123'}
                            }
                        
                        mock_request.side_effect = capture_order
                        
                        # Place order with stop loss below minimum
                        self.bot.place_order(instrument, 'BUY', 10, sl_pips, tp_pips, 1800.00)
                        
                        # Check that stop loss was adjusted
                        self.assertIsNotNone(self.order_data)
                        sl_distance = float(self.order_data['order']['stopLossOnFill']['distance'])
                        
                        # The adjusted SL should be at least the minimum (0.05)
                        self.assertGreaterEqual(sl_distance, 0.05,
                                              f"SL distance {sl_distance} is below minimum 0.05")


if __name__ == '__main__':
    unittest.main()
