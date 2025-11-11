"""
Unit test for the OandaTradingBot initialization order fix.
Tests that all components are properly initialized before API calls.
"""
import unittest
from unittest.mock import MagicMock, patch, Mock


class TestInitializationOrder(unittest.TestCase):
    """Test OandaTradingBot initialization order."""
    
    def test_initialization_order_with_api_call(self):
        """Test that bot initializes without AttributeError when API is called."""
        from bot import OandaTradingBot
        
        # Mock responses for API calls
        mock_balance_response = {
            'account': {
                'balance': '10000.0'
            }
        }
        
        mock_instruments_response = {
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
                }
            ]
        }
        
        # Mock the API to return proper responses
        with patch('bot.oandapyV20.API') as MockAPI, \
             patch('bot.TradeDatabase'), \
             patch('bot.MLPredictor'), \
             patch('bot.PositionSizer'), \
             patch('bot.MultiTimeframeAnalyzer'), \
             patch('bot.AdaptiveThresholdManager'), \
             patch('bot.VolatilityDetector'):
            
            # Create a mock API instance
            mock_api = Mock()
            MockAPI.return_value = mock_api
            
            # Mock the request method to return appropriate responses
            def mock_request(endpoint):
                endpoint_name = endpoint.__class__.__name__
                if 'AccountSummary' in endpoint_name:
                    return mock_balance_response
                elif 'AccountInstruments' in endpoint_name:
                    return mock_instruments_response
                else:
                    return {}
            
            mock_api.request = Mock(side_effect=mock_request)
            
            # This should NOT raise AttributeError
            try:
                bot = OandaTradingBot(
                    enable_ml=False,
                    enable_multiframe=False,
                    enable_adaptive_threshold=False,
                    enable_volatility_detection=False
                )
                
                # Verify bot was initialized successfully
                self.assertIsNotNone(bot)
                self.assertEqual(bot.daily_start_balance, 10000.0)
                
                # Verify all components are initialized
                self.assertIsNotNone(bot.data_validator)
                self.assertIsNotNone(bot.structured_logger)
                self.assertIsNotNone(bot.performance_monitor)
                self.assertIsNotNone(bot.api_backoff)
                
                # Verify initialization order: components exist before balance call
                self.assertTrue(hasattr(bot, 'data_validator'))
                self.assertTrue(hasattr(bot, 'structured_logger'))
                self.assertTrue(hasattr(bot, 'performance_monitor'))
                
            except AttributeError as e:
                self.fail(f"Initialization failed with AttributeError: {e}")
    
    def test_api_call_before_components_initialized_handled_gracefully(self):
        """Test that API calls handle missing components gracefully."""
        from bot import OandaTradingBot
        
        # Mock responses
        mock_balance_response = {
            'account': {
                'balance': '5000.0'
            }
        }
        
        with patch('bot.oandapyV20.API') as MockAPI, \
             patch('bot.TradeDatabase'), \
             patch('bot.MLPredictor'), \
             patch('bot.PositionSizer'), \
             patch('bot.MultiTimeframeAnalyzer'), \
             patch('bot.AdaptiveThresholdManager'), \
             patch('bot.VolatilityDetector'):
            
            mock_api = Mock()
            MockAPI.return_value = mock_api
            mock_api.request = Mock(return_value=mock_balance_response)
            
            # Initialize bot with disabled features
            bot = OandaTradingBot(
                enable_ml=False,
                enable_multiframe=False,
                enable_adaptive_threshold=False,
                enable_volatility_detection=False
            )
            
            # Verify components that should exist
            self.assertIsNotNone(bot.data_validator)
            
            # Verify balance was set correctly
            self.assertEqual(bot.daily_start_balance, 5000.0)
    
    def test_components_initialized_before_dynamic_instruments_fetch(self):
        """Test that components are ready before dynamic instruments are fetched."""
        from bot import OandaTradingBot
        
        mock_instruments_response = {
            'instruments': [
                {
                    'name': 'USD_JPY',
                    'displayName': 'USD/JPY',
                    'type': 'CURRENCY',
                    'pipLocation': -2,
                    'displayPrecision': 3,
                    'tradeUnitsPrecision': 0,
                    'minimumTradeSize': '1',
                    'maximumOrderUnits': '100000000'
                }
            ]
        }
        
        mock_balance_response = {
            'account': {
                'balance': '15000.0'
            }
        }
        
        with patch('bot.oandapyV20.API') as MockAPI, \
             patch('bot.TradeDatabase'), \
             patch('bot.MLPredictor'), \
             patch('bot.PositionSizer'), \
             patch('bot.MultiTimeframeAnalyzer'), \
             patch('bot.AdaptiveThresholdManager'), \
             patch('bot.VolatilityDetector'), \
             patch('bot.ENABLE_DYNAMIC_INSTRUMENTS', True):
            
            mock_api = Mock()
            MockAPI.return_value = mock_api
            
            def mock_request(endpoint):
                endpoint_name = endpoint.__class__.__name__
                if 'AccountSummary' in endpoint_name:
                    return mock_balance_response
                elif 'AccountInstruments' in endpoint_name:
                    return mock_instruments_response
                else:
                    return {}
            
            mock_api.request = Mock(side_effect=mock_request)
            
            # This should initialize without errors even with dynamic instruments enabled
            bot = OandaTradingBot(
                enable_ml=False,
                enable_multiframe=False,
                enable_adaptive_threshold=False,
                enable_volatility_detection=False
            )
            
            # Verify bot initialized successfully
            self.assertIsNotNone(bot)
            self.assertEqual(bot.daily_start_balance, 15000.0)
            
            # Verify instruments cache was populated
            self.assertGreater(len(bot.instruments_cache), 0)
            self.assertIn('USD_JPY', bot.instruments_cache)


if __name__ == '__main__':
    unittest.main()
