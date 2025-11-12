"""
Unit tests for string parameter conversion in calculate_auto_scaled_units.
Tests that current_price and margin_rate are properly converted from strings to floats.
"""
import unittest
from position_sizing import PositionSizer


class TestStringParameterConversion(unittest.TestCase):
    """Test that string parameters are properly converted to floats."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.02,
            min_trade_value=1.50
        )
    
    def test_string_current_price(self):
        """Test that string current_price is converted to float."""
        balance = 1000.0
        stop_loss_pips = 10.0
        pip_value = 0.0001
        current_price = "1.2000"  # String instead of float
        available_margin = 900.0
        margin_rate = 0.0333
        minimum_trade_size = '1'
        trade_units_precision = 0
        maximum_order_units = '100000000'
        risk_per_trade = 0.02
        max_units_per_instrument = 100000
        min_trade_value = 1.50
        margin_buffer = 0.5
        
        units, risk_pct, debug = self.sizer.calculate_auto_scaled_units(
            balance=balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            current_price=current_price,
            available_margin=available_margin,
            margin_rate=margin_rate,
            minimum_trade_size=minimum_trade_size,
            trade_units_precision=trade_units_precision,
            maximum_order_units=maximum_order_units,
            risk_per_trade=risk_per_trade,
            max_units_per_instrument=max_units_per_instrument,
            min_trade_value=min_trade_value,
            margin_buffer=margin_buffer
        )
        
        # Should successfully convert and compute units
        self.assertGreater(units, 0, "Should compute positive units even with string current_price")
        self.assertNotIn('reason', debug, "Should not have skip reason with valid string current_price")
        print(f"\nString current_price test: units={units}, risk_pct={risk_pct*100:.2f}%")
    
    def test_string_margin_rate(self):
        """Test that string margin_rate is converted to float."""
        balance = 1000.0
        stop_loss_pips = 10.0
        pip_value = 0.0001
        current_price = 1.2000
        available_margin = 900.0
        margin_rate = "0.0333"  # String instead of float
        minimum_trade_size = '1'
        trade_units_precision = 0
        maximum_order_units = '100000000'
        risk_per_trade = 0.02
        max_units_per_instrument = 100000
        min_trade_value = 1.50
        margin_buffer = 0.5
        
        units, risk_pct, debug = self.sizer.calculate_auto_scaled_units(
            balance=balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            current_price=current_price,
            available_margin=available_margin,
            margin_rate=margin_rate,
            minimum_trade_size=minimum_trade_size,
            trade_units_precision=trade_units_precision,
            maximum_order_units=maximum_order_units,
            risk_per_trade=risk_per_trade,
            max_units_per_instrument=max_units_per_instrument,
            min_trade_value=min_trade_value,
            margin_buffer=margin_buffer
        )
        
        # Should successfully convert and compute units
        self.assertGreater(units, 0, "Should compute positive units even with string margin_rate")
        self.assertNotIn('reason', debug, "Should not have skip reason with valid string margin_rate")
        print(f"\nString margin_rate test: units={units}, risk_pct={risk_pct*100:.2f}%")
    
    def test_both_strings(self):
        """Test that both current_price and margin_rate as strings work."""
        balance = 1000.0
        stop_loss_pips = 10.0
        pip_value = 0.0001
        current_price = "1.2000"  # String
        available_margin = 900.0
        margin_rate = "0.0333"  # String
        minimum_trade_size = '1'
        trade_units_precision = 0
        maximum_order_units = '100000000'
        risk_per_trade = 0.02
        max_units_per_instrument = 100000
        min_trade_value = 1.50
        margin_buffer = 0.5
        
        units, risk_pct, debug = self.sizer.calculate_auto_scaled_units(
            balance=balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            current_price=current_price,
            available_margin=available_margin,
            margin_rate=margin_rate,
            minimum_trade_size=minimum_trade_size,
            trade_units_precision=trade_units_precision,
            maximum_order_units=maximum_order_units,
            risk_per_trade=risk_per_trade,
            max_units_per_instrument=max_units_per_instrument,
            min_trade_value=min_trade_value,
            margin_buffer=margin_buffer
        )
        
        # Should successfully convert and compute units
        self.assertGreater(units, 0, "Should compute positive units even with both as strings")
        self.assertNotIn('reason', debug, "Should not have skip reason with valid string parameters")
        print(f"\nBoth strings test: units={units}, risk_pct={risk_pct*100:.2f}%")
    
    def test_invalid_current_price(self):
        """Test that invalid current_price returns 0."""
        balance = 1000.0
        stop_loss_pips = 10.0
        pip_value = 0.0001
        current_price = "invalid"  # Invalid string
        available_margin = 900.0
        margin_rate = 0.0333
        minimum_trade_size = '1'
        trade_units_precision = 0
        maximum_order_units = '100000000'
        risk_per_trade = 0.02
        max_units_per_instrument = 100000
        min_trade_value = 1.50
        margin_buffer = 0.5
        
        units, risk_pct, debug = self.sizer.calculate_auto_scaled_units(
            balance=balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            current_price=current_price,
            available_margin=available_margin,
            margin_rate=margin_rate,
            minimum_trade_size=minimum_trade_size,
            trade_units_precision=trade_units_precision,
            maximum_order_units=maximum_order_units,
            risk_per_trade=risk_per_trade,
            max_units_per_instrument=max_units_per_instrument,
            min_trade_value=min_trade_value,
            margin_buffer=margin_buffer
        )
        
        # Should return 0 with reason
        self.assertEqual(units, 0, "Should return 0 units with invalid current_price")
        self.assertIn('reason', debug, "Debug should contain skip reason")
        self.assertIn('current_price', debug['reason'].lower(), 
                     f"Reason should mention current_price: {debug['reason']}")
        print(f"\nInvalid current_price test: {debug['reason']}")
    
    def test_invalid_margin_rate(self):
        """Test that invalid margin_rate returns 0."""
        balance = 1000.0
        stop_loss_pips = 10.0
        pip_value = 0.0001
        current_price = 1.2000
        available_margin = 900.0
        margin_rate = "invalid"  # Invalid string
        minimum_trade_size = '1'
        trade_units_precision = 0
        maximum_order_units = '100000000'
        risk_per_trade = 0.02
        max_units_per_instrument = 100000
        min_trade_value = 1.50
        margin_buffer = 0.5
        
        units, risk_pct, debug = self.sizer.calculate_auto_scaled_units(
            balance=balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            current_price=current_price,
            available_margin=available_margin,
            margin_rate=margin_rate,
            minimum_trade_size=minimum_trade_size,
            trade_units_precision=trade_units_precision,
            maximum_order_units=maximum_order_units,
            risk_per_trade=risk_per_trade,
            max_units_per_instrument=max_units_per_instrument,
            min_trade_value=min_trade_value,
            margin_buffer=margin_buffer
        )
        
        # Should return 0 with reason
        self.assertEqual(units, 0, "Should return 0 units with invalid margin_rate")
        self.assertIn('reason', debug, "Debug should contain skip reason")
        self.assertIn('margin_rate', debug['reason'].lower(), 
                     f"Reason should mention margin_rate: {debug['reason']}")
        print(f"\nInvalid margin_rate test: {debug['reason']}")
    
    def test_none_current_price(self):
        """Test that None current_price returns 0."""
        balance = 1000.0
        stop_loss_pips = 10.0
        pip_value = 0.0001
        current_price = None  # None value
        available_margin = 900.0
        margin_rate = 0.0333
        minimum_trade_size = '1'
        trade_units_precision = 0
        maximum_order_units = '100000000'
        risk_per_trade = 0.02
        max_units_per_instrument = 100000
        min_trade_value = 1.50
        margin_buffer = 0.5
        
        units, risk_pct, debug = self.sizer.calculate_auto_scaled_units(
            balance=balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            current_price=current_price,
            available_margin=available_margin,
            margin_rate=margin_rate,
            minimum_trade_size=minimum_trade_size,
            trade_units_precision=trade_units_precision,
            maximum_order_units=maximum_order_units,
            risk_per_trade=risk_per_trade,
            max_units_per_instrument=max_units_per_instrument,
            min_trade_value=min_trade_value,
            margin_buffer=margin_buffer
        )
        
        # Should return 0 with reason
        self.assertEqual(units, 0, "Should return 0 units with None current_price")
        self.assertIn('reason', debug, "Debug should contain skip reason")
        print(f"\nNone current_price test: {debug['reason']}")
    
    def test_none_margin_rate(self):
        """Test that None margin_rate returns 0."""
        balance = 1000.0
        stop_loss_pips = 10.0
        pip_value = 0.0001
        current_price = 1.2000
        available_margin = 900.0
        margin_rate = None  # None value
        minimum_trade_size = '1'
        trade_units_precision = 0
        maximum_order_units = '100000000'
        risk_per_trade = 0.02
        max_units_per_instrument = 100000
        min_trade_value = 1.50
        margin_buffer = 0.5
        
        units, risk_pct, debug = self.sizer.calculate_auto_scaled_units(
            balance=balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            current_price=current_price,
            available_margin=available_margin,
            margin_rate=margin_rate,
            minimum_trade_size=minimum_trade_size,
            trade_units_precision=trade_units_precision,
            maximum_order_units=maximum_order_units,
            risk_per_trade=risk_per_trade,
            max_units_per_instrument=max_units_per_instrument,
            min_trade_value=min_trade_value,
            margin_buffer=margin_buffer
        )
        
        # Should return 0 with reason
        self.assertEqual(units, 0, "Should return 0 units with None margin_rate")
        self.assertIn('reason', debug, "Debug should contain skip reason")
        print(f"\nNone margin_rate test: {debug['reason']}")


if __name__ == '__main__':
    unittest.main()
