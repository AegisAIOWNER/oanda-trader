"""
Unit tests for pip value calculation.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from bot import OandaTradingBot


class TestPipValueCalculation(unittest.TestCase):
    """Test pip value calculation for different instruments."""
    
    def setUp(self):
        """Set up test bot instance with mocked API."""
        with patch('bot.oandapyV20.API'):
            with patch.object(OandaTradingBot, '_rate_limited_request') as mock_request:
                # Mock the account summary response for balance
                mock_request.return_value = {
                    'account': {'balance': '10000.0'}
                }
                
                # Mock instruments cache
                mock_instruments_response = {
                    'instruments': [
                        {
                            'name': 'EUR_USD',
                            'pipLocation': -4,
                            'displayName': 'EUR/USD',
                            'type': 'CURRENCY'
                        },
                        {
                            'name': 'USD_JPY',
                            'pipLocation': -2,
                            'displayName': 'USD/JPY',
                            'type': 'CURRENCY'
                        },
                        {
                            'name': 'GBP_NZD',
                            'pipLocation': -4,
                            'displayName': 'GBP/NZD',
                            'type': 'CURRENCY'
                        }
                    ]
                }
                
                # Create bot with mocked responses
                original_rate_limited = OandaTradingBot._rate_limited_request
                
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
    
    def test_pip_value_eur_usd(self):
        """Test pip value calculation for EUR_USD."""
        # EUR_USD at 1.1000, pip size = 0.0001
        # pip_value (per unit) = pip_size = 0.0001
        instrument = 'EUR_USD'
        price = 1.1000
        
        pip_value = self.bot._calculate_pip_value(instrument, price)
        
        # For EUR_USD, pip value per unit equals pip size
        self.assertAlmostEqual(pip_value, 0.0001, places=5)
    
    def test_pip_value_usd_jpy(self):
        """Test pip value calculation for USD_JPY."""
        # USD_JPY at 110.00, pip size = 0.01
        # pip_value (per unit) = pip_size = 0.01
        instrument = 'USD_JPY'
        price = 110.00
        
        pip_value = self.bot._calculate_pip_value(instrument, price)
        
        # USD_JPY pip value per unit equals pip size
        self.assertAlmostEqual(pip_value, 0.01, places=5)
    
    def test_pip_value_gbp_nzd(self):
        """Test pip value calculation for GBP_NZD (exotic pair)."""
        # GBP_NZD at 1.9500, pip size = 0.0001
        # pip_value (per unit) = pip_size = 0.0001
        instrument = 'GBP_NZD'
        price = 1.9500
        
        pip_value = self.bot._calculate_pip_value(instrument, price)
        
        # Should calculate based on pip size, not use hardcoded value
        self.assertAlmostEqual(pip_value, 0.0001, places=5)
    
    def test_pip_value_with_invalid_price(self):
        """Test pip value calculation with invalid price."""
        instrument = 'EUR_USD'
        
        # Even with invalid price, should return pip size (0.0001 for EUR_USD)
        # Test with zero price
        pip_value = self.bot._calculate_pip_value(instrument, 0)
        self.assertAlmostEqual(pip_value, 0.0001, places=5)
        
        # Test with negative price
        pip_value = self.bot._calculate_pip_value(instrument, -1.0)
        self.assertAlmostEqual(pip_value, 0.0001, places=5)
        
        # Test with None
        pip_value = self.bot._calculate_pip_value(instrument, None)
        self.assertAlmostEqual(pip_value, 0.0001, places=5)
    
    def test_pip_value_with_invalid_instrument(self):
        """Test pip value calculation with invalid instrument."""
        # Test with invalid format - should fall back to default pip size (0.0001)
        pip_value = self.bot._calculate_pip_value('INVALID', 1.0)
        self.assertAlmostEqual(pip_value, 0.0001, places=5)
        
        # Test with empty string - should fall back to default pip size (0.0001)
        pip_value = self.bot._calculate_pip_value('', 1.0)
        self.assertAlmostEqual(pip_value, 0.0001, places=5)
    
    def test_pip_size_retrieval_eur_usd(self):
        """Test that pip size is correctly retrieved for EUR_USD."""
        instrument = 'EUR_USD'
        pip_size = self.bot._get_instrument_pip_size(instrument)
        
        # EUR_USD should have pip size of 0.0001
        self.assertAlmostEqual(pip_size, 0.0001, places=5)
    
    def test_pip_size_retrieval_usd_jpy(self):
        """Test that pip size is correctly retrieved for USD_JPY."""
        instrument = 'USD_JPY'
        pip_size = self.bot._get_instrument_pip_size(instrument)
        
        # USD_JPY should have pip size of 0.01
        self.assertAlmostEqual(pip_size, 0.01, places=5)
    
    def test_pip_size_retrieval_gbp_nzd(self):
        """Test that pip size is correctly retrieved for GBP_NZD."""
        instrument = 'GBP_NZD'
        pip_size = self.bot._get_instrument_pip_size(instrument)
        
        # GBP_NZD should have pip size of 0.0001
        self.assertAlmostEqual(pip_size, 0.0001, places=5)


class TestRiskCalculationWithPipValue(unittest.TestCase):
    """Test risk calculation using proper pip values."""
    
    def setUp(self):
        """Set up test bot instance with mocked API."""
        with patch('bot.oandapyV20.API'):
            with patch.object(OandaTradingBot, '_rate_limited_request') as mock_request:
                # Mock responses
                mock_instruments_response = {
                    'instruments': [
                        {
                            'name': 'EUR_USD',
                            'pipLocation': -4,
                            'displayName': 'EUR/USD',
                            'type': 'CURRENCY'
                        },
                        {
                            'name': 'GBP_NZD',
                            'pipLocation': -4,
                            'displayName': 'GBP/NZD',
                            'type': 'CURRENCY'
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
    
    def test_risk_amount_calculation_eur_usd(self):
        """Test that risk amount is calculated correctly for EUR_USD."""
        instrument = 'EUR_USD'
        price = 1.1000
        units = 10000  # 0.1 lot
        sl_pips = 10  # 10 pips stop loss
        
        pip_value = self.bot._calculate_pip_value(instrument, price)
        
        # Risk amount = units * sl_pips * pip_value
        # = 10000 * 10 * 0.0001 = 10
        expected_risk = units * sl_pips * pip_value
        self.assertAlmostEqual(expected_risk, 10.0, places=2)
    
    def test_risk_amount_calculation_gbp_nzd(self):
        """Test that risk amount is calculated correctly for GBP_NZD."""
        instrument = 'GBP_NZD'
        price = 1.9500
        units = 10000  # 0.1 lot
        sl_pips = 10  # 10 pips stop loss
        
        pip_value = self.bot._calculate_pip_value(instrument, price)
        
        # Should use calculated pip value, not hardcoded value
        # Risk amount = units * sl_pips * pip_value
        # = 10000 * 10 * 0.0001 = 10
        expected_risk = units * sl_pips * pip_value
        
        # This should be the same as EUR_USD since both have pip_size = 0.0001
        self.assertAlmostEqual(expected_risk, 10.0, places=2)


if __name__ == '__main__':
    unittest.main()
