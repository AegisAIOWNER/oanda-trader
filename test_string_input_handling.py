"""
Unit tests for handling string inputs in position sizing.
Tests that string inputs (from API metadata) are correctly converted and don't raise TypeErrors.
"""
import unittest
from position_sizing import PositionSizer


class TestStringInputHandling(unittest.TestCase):
    """Test string input handling in position sizing calculations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.02,
            min_trade_value=1.50
        )
    
    def test_all_string_inputs(self):
        """Test case where all numeric inputs are strings (as from API metadata)."""
        # All metadata values as strings
        balance = 1000.0
        stop_loss_pips = 10.0
        pip_value = 0.0001
        current_price = "1.2000"  # String
        available_margin = 900.0
        margin_rate = "0.0333"  # String from instrument metadata
        minimum_trade_size = '1'  # String from instrument metadata
        trade_units_precision = '0'  # String from instrument metadata
        maximum_order_units = '100000000'  # String from instrument metadata
        risk_per_trade = 0.02
        max_units_per_instrument = 100000
        min_trade_value = 1.50
        margin_buffer = 0.5
        
        # Should not raise TypeError
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
        
        # Should successfully compute units
        self.assertGreater(units, 0, "Should compute positive units with string inputs")
        self.assertNotIn('reason', debug, "Should not have skip reason")
        
        # Verify risk is within limits
        self.assertLessEqual(risk_pct, risk_per_trade,
                            f"Risk {risk_pct*100:.2f}% should be <= {risk_per_trade*100:.2f}%")
        
        print(f"\nAll-string-inputs test:")
        print(f"  final units: {units}")
        print(f"  risk_pct: {risk_pct*100:.2f}%")
    
    def test_string_margin_rate_and_minimum_trade_size(self):
        """Test with string marginRate and minimumTradeSize (common API response format)."""
        balance = 500.0
        stop_loss_pips = 15.0
        pip_value = 0.0001
        current_price = 1.1000
        available_margin = 400.0
        margin_rate = "0.05"  # String: 5% margin requirement (20:1 leverage)
        minimum_trade_size = "100"  # String: minimum 100 units
        trade_units_precision = 0
        maximum_order_units = "10000000"  # String
        risk_per_trade = 0.02
        max_units_per_instrument = 50000
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
        
        # Should successfully compute units
        self.assertGreater(units, 0, "Should compute positive units")
        
        # Verify units meet minimum trade size (parsed from string)
        self.assertGreaterEqual(units, 100, "Units should meet minimum trade size of 100")
        
        print(f"\nString margin_rate and min_trade_size test:")
        print(f"  units_by_margin: {debug['units_by_margin']}")
        print(f"  units_by_risk: {debug['units_by_risk']}")
        print(f"  final units: {units}")
        print(f"  min_trade_size (parsed): {debug['min_trade_size']}")
    
    def test_string_trade_units_precision(self):
        """Test with string tradeUnitsPrecision for rounding."""
        balance = 1000.0
        stop_loss_pips = 10.0
        pip_value = 0.0001
        current_price = 1.2000
        available_margin = 900.0
        margin_rate = 0.0333
        minimum_trade_size = 1
        trade_units_precision = "-1"  # String: round to nearest 10
        maximum_order_units = 100000000
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
        
        # Verify units are rounded to nearest 10
        self.assertEqual(units % 10, 0, "Units should be rounded to nearest 10")
        
        print(f"\nString trade_units_precision (-1) test:")
        print(f"  candidate_units_before_rounding: {debug['candidate_units_before_rounding']}")
        print(f"  final units (rounded to 10s): {units}")
    
    def test_invalid_string_inputs_use_defaults(self):
        """Test that invalid string inputs fall back to safe defaults."""
        balance = 100.0
        stop_loss_pips = 10.0
        pip_value = 0.0001
        current_price = "invalid"  # Invalid string
        available_margin = 50.0
        margin_rate = "not_a_number"  # Invalid string
        minimum_trade_size = "xyz"  # Invalid string
        trade_units_precision = "abc"  # Invalid string
        maximum_order_units = "bad_value"  # Invalid string
        risk_per_trade = 0.02
        max_units_per_instrument = 100000
        min_trade_value = 1.50
        margin_buffer = 0.5
        
        # Should not raise TypeError, should use defaults
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
        
        # Should return 0 units due to invalid price (defaults to 0.0)
        self.assertEqual(units, 0, "Should return 0 units when price is invalid")
        self.assertIn('reason', debug, "Should have skip reason")
        self.assertIn('price', debug['reason'].lower(), "Reason should mention price")
        
        print(f"\nInvalid string inputs test:")
        print(f"  Reason: {debug['reason']}")
    
    def test_mixed_string_and_numeric_inputs(self):
        """Test with a realistic mix of string and numeric inputs."""
        balance = 2000.0
        stop_loss_pips = 20.0
        pip_value = 0.0001
        current_price = "1.0850"  # String
        available_margin = 1800.0
        margin_rate = "0.04"  # String: 4% margin
        minimum_trade_size = "1"  # String
        trade_units_precision = 0  # Numeric
        maximum_order_units = "50000000"  # String
        risk_per_trade = 0.015  # Numeric
        max_units_per_instrument = 200000  # Numeric
        min_trade_value = 2.0  # Numeric
        margin_buffer = 0.3  # Numeric
        
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
        
        # Should successfully compute units
        self.assertGreater(units, 0, "Should compute positive units with mixed inputs")
        
        # Verify constraints are respected
        self.assertLessEqual(units, debug['units_by_margin'],
                            "Units should not exceed margin constraint")
        self.assertLessEqual(units, debug['units_by_risk'],
                            "Units should not exceed risk constraint")
        
        print(f"\nMixed string/numeric inputs test:")
        print(f"  final units: {units}")
        print(f"  risk_pct: {risk_pct*100:.2f}%")
    
    def test_string_zero_values(self):
        """Test with string zeros in inputs."""
        balance = 100.0
        stop_loss_pips = 10.0
        pip_value = 0.0001
        current_price = "0.0"  # String zero
        available_margin = 50.0
        margin_rate = "0.0333"
        minimum_trade_size = "1"
        trade_units_precision = "0"
        maximum_order_units = "100000000"
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
        
        # Should return 0 units due to zero price
        self.assertEqual(units, 0, "Should return 0 units when price is zero")
        self.assertIn('reason', debug, "Should have skip reason")
        
        print(f"\nString zero values test:")
        print(f"  Reason: {debug['reason']}")
    
    def test_helper_to_float(self):
        """Test the _to_float helper method directly."""
        # Valid conversions
        self.assertEqual(self.sizer._to_float("1.234"), 1.234)
        self.assertEqual(self.sizer._to_float("100"), 100.0)
        self.assertEqual(self.sizer._to_float(50), 50.0)
        self.assertEqual(self.sizer._to_float(3.14), 3.14)
        
        # Invalid conversions should use default
        self.assertEqual(self.sizer._to_float("invalid", 5.0), 5.0)
        self.assertEqual(self.sizer._to_float(None, 10.0), 10.0)
        self.assertEqual(self.sizer._to_float("", 2.0), 2.0)
        
        print("\n_to_float helper test: All conversions work correctly")
    
    def test_helper_to_int(self):
        """Test the _to_int helper method directly."""
        # Valid conversions
        self.assertEqual(self.sizer._to_int("123"), 123)
        self.assertEqual(self.sizer._to_int("1.9"), 1)  # Truncates
        self.assertEqual(self.sizer._to_int(50), 50)
        self.assertEqual(self.sizer._to_int(3.7), 3)
        
        # Invalid conversions should use default
        self.assertEqual(self.sizer._to_int("invalid", 5), 5)
        self.assertEqual(self.sizer._to_int(None, 10), 10)
        self.assertEqual(self.sizer._to_int("", 2), 2)
        
        print("\n_to_int helper test: All conversions work correctly")


if __name__ == '__main__':
    unittest.main()
