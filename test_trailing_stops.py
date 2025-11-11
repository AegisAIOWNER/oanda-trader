"""
Tests for trailing stop loss functionality.
"""
import unittest
from trailing_stops import TrailingStopManager


class TestTrailingStopManager(unittest.TestCase):
    """Test cases for TrailingStopManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.manager = TrailingStopManager(atr_multiplier=0.5, activation_multiplier=1.0)
    
    def test_initialization(self):
        """Test manager initialization."""
        self.assertEqual(self.manager.atr_multiplier, 0.5)
        self.assertEqual(self.manager.activation_multiplier, 1.0)
        self.assertEqual(len(self.manager.position_trailing_state), 0)
    
    def test_should_activate_trailing_not_enough_profit(self):
        """Test trailing doesn't activate with insufficient profit."""
        # Profit is 5 pips, ATR is 10 pips, activation threshold is 1.0x ATR = 10 pips
        result = self.manager.should_activate_trailing('EUR_USD', current_profit_pips=5, atr_pips=10)
        self.assertFalse(result)
    
    def test_should_activate_trailing_enough_profit(self):
        """Test trailing activates with sufficient profit."""
        # Profit is 15 pips, ATR is 10 pips, activation threshold is 1.0x ATR = 10 pips
        result = self.manager.should_activate_trailing('EUR_USD', current_profit_pips=15, atr_pips=10)
        self.assertTrue(result)
    
    def test_calculate_new_stop_loss_buy_not_activated(self):
        """Test trailing stop doesn't update before activation threshold for BUY."""
        instrument = 'EUR_USD'
        direction = 'BUY'
        entry_price = 1.1000
        current_price = 1.1050  # 50 pips profit
        current_sl_price = 1.0950  # 50 pips below entry
        atr_pips = 100  # 100 pips ATR, so need 100 pips profit to activate
        pip_size = 0.0001
        
        new_sl, move_pips, should_update = self.manager.calculate_new_stop_loss(
            instrument, direction, entry_price, current_price, current_sl_price, atr_pips, pip_size
        )
        
        self.assertFalse(should_update)
        self.assertEqual(new_sl, current_sl_price)
    
    def test_calculate_new_stop_loss_buy_activated(self):
        """Test trailing stop updates after activation for BUY."""
        instrument = 'EUR_USD'
        direction = 'BUY'
        entry_price = 1.1000
        current_price = 1.1150  # 150 pips profit
        current_sl_price = 1.0950  # 50 pips below entry
        atr_pips = 100  # 100 pips ATR, activation threshold met
        pip_size = 0.0001
        
        new_sl, move_pips, should_update = self.manager.calculate_new_stop_loss(
            instrument, direction, entry_price, current_price, current_sl_price, atr_pips, pip_size
        )
        
        self.assertTrue(should_update)
        self.assertGreater(new_sl, current_sl_price)  # SL should move up
        self.assertLess(new_sl, current_price)  # But still below current price
    
    def test_calculate_new_stop_loss_sell_activated(self):
        """Test trailing stop updates after activation for SELL."""
        instrument = 'EUR_USD'
        direction = 'SELL'
        entry_price = 1.1000
        current_price = 1.0850  # 150 pips profit (price went down)
        current_sl_price = 1.1050  # 50 pips above entry
        atr_pips = 100  # 100 pips ATR, activation threshold met
        pip_size = 0.0001
        
        new_sl, move_pips, should_update = self.manager.calculate_new_stop_loss(
            instrument, direction, entry_price, current_price, current_sl_price, atr_pips, pip_size
        )
        
        self.assertTrue(should_update)
        self.assertLess(new_sl, current_sl_price)  # SL should move down for SELL
        self.assertGreater(new_sl, current_price)  # But still above current price
    
    def test_get_trailing_stats_no_state(self):
        """Test getting stats for instrument with no trailing state."""
        stats = self.manager.get_trailing_stats('EUR_USD')
        self.assertFalse(stats['active'])
        self.assertEqual(stats['total_moves'], 0)
    
    def test_get_trailing_stats_with_state(self):
        """Test getting stats after trailing is activated."""
        instrument = 'EUR_USD'
        direction = 'BUY'
        entry_price = 1.1000
        current_price = 1.1150
        current_sl_price = 1.0950
        atr_pips = 100
        pip_size = 0.0001
        
        # Activate trailing
        self.manager.calculate_new_stop_loss(
            instrument, direction, entry_price, current_price, current_sl_price, atr_pips, pip_size
        )
        
        stats = self.manager.get_trailing_stats(instrument)
        self.assertTrue(stats['active'])
        self.assertGreater(stats['total_moves'], 0)
    
    def test_clear_instrument_state(self):
        """Test clearing trailing state."""
        instrument = 'EUR_USD'
        
        # Set up some state
        self.manager.position_trailing_state[instrument] = {
            'highest_price': 1.1150,
            'total_moves': 2
        }
        
        self.manager.clear_instrument_state(instrument)
        
        stats = self.manager.get_trailing_stats(instrument)
        self.assertFalse(stats['active'])
    
    def test_get_all_active_instruments(self):
        """Test getting list of active instruments."""
        # Add some trailing states
        self.manager.position_trailing_state['EUR_USD'] = {'total_moves': 1}
        self.manager.position_trailing_state['GBP_USD'] = {'total_moves': 2}
        
        active = self.manager.get_all_active_instruments()
        self.assertEqual(len(active), 2)
        self.assertIn('EUR_USD', active)
        self.assertIn('GBP_USD', active)


if __name__ == '__main__':
    unittest.main()
