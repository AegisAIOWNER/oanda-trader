"""
Unit tests for auto-scaling position sizing.
Tests that auto-scaling correctly computes units within margin and risk constraints.
"""
import unittest
from position_sizing import PositionSizer


class TestAutoScaleUnits(unittest.TestCase):
    """Test auto-scaling position sizing calculations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.02,
            min_trade_value=1.50
        )
    
    def test_margin_limited_case(self):
        """Test case where margin is the limiting factor."""
        # Small balance scenario: EUR_USD with tight margin
        balance = 20.0
        stop_loss_pips = 10.0
        pip_value = 0.0001
        current_price = 1.1000
        available_margin = 15.0  # Limited margin
        margin_rate = 0.0333  # ~30:1 leverage
        minimum_trade_size = '1'
        trade_units_precision = 0
        maximum_order_units = '100000000'
        risk_per_trade = 0.02
        max_units_per_instrument = 100000
        min_trade_value = 1.50
        margin_buffer = 0.5  # 50% buffer
        
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
        
        # Verify units are positive
        self.assertGreater(units, 0, "Units should be positive in margin-limited case")
        
        # Verify units meet minimum trade size
        self.assertGreaterEqual(units, float(minimum_trade_size), 
                                "Units should meet minimum trade size")
        
        # Verify units_by_margin is less than or equal to units_by_risk (margin-limited)
        self.assertLessEqual(debug['units_by_margin'], debug['units_by_risk'],
                             "Should be margin-limited: units_by_margin <= units_by_risk")
        
        # Verify final units equals units_by_margin (the limiting factor)
        self.assertEqual(units, debug['units_by_margin'],
                        "Final units should equal units_by_margin in margin-limited case")
        
        # Verify trade value meets minimum
        trade_value = units * current_price
        self.assertGreaterEqual(trade_value, min_trade_value,
                                f"Trade value ${trade_value:.2f} should be >= ${min_trade_value:.2f}")
        
        # Log debug info for visibility
        print(f"\nMargin-limited test:")
        print(f"  units_by_margin: {debug['units_by_margin']}")
        print(f"  units_by_risk: {debug['units_by_risk']}")
        print(f"  final units: {units}")
        print(f"  risk_pct: {risk_pct*100:.2f}%")
    
    def test_risk_limited_case(self):
        """Test case where risk is the limiting factor (huge ATR/wide stop)."""
        # Large stop loss scenario - risk becomes limiting
        balance = 100.0
        stop_loss_pips = 200.0  # Very wide stop
        pip_value = 0.0001
        current_price = 1.1000
        available_margin = 90.0  # Plenty of margin
        margin_rate = 0.0333
        minimum_trade_size = '1'
        trade_units_precision = 0
        maximum_order_units = '100000000'
        risk_per_trade = 0.02
        max_units_per_instrument = 100000
        min_trade_value = 1.50
        margin_buffer = 0.1  # Small buffer for more margin
        
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
        
        # With very wide stop, units_by_risk should be very low or zero
        # This might cause the function to return 0 units if below minimum
        
        if units == 0:
            # Expected outcome: risk constraint makes position too small
            self.assertIn('reason', debug, "Debug should contain skip reason")
            self.assertTrue(
                'minimum' in debug['reason'].lower() or 'risk' in debug['reason'].lower(),
                f"Skip reason should mention minimum or risk: {debug['reason']}"
            )
            print(f"\nRisk-limited test (skipped):")
            print(f"  Reason: {debug['reason']}")
            print(f"  units_by_risk: {debug.get('units_by_risk', 0)}")
            print(f"  units_by_margin: {debug.get('units_by_margin', 0)}")
        else:
            # If units > 0, verify it's risk-limited
            self.assertLessEqual(debug['units_by_risk'], debug['units_by_margin'],
                                "Should be risk-limited: units_by_risk <= units_by_margin")
            print(f"\nRisk-limited test (executed):")
            print(f"  units_by_risk: {debug['units_by_risk']}")
            print(f"  units_by_margin: {debug['units_by_margin']}")
            print(f"  final units: {units}")
            print(f"  risk_pct: {risk_pct*100:.2f}%")
    
    def test_below_minimum_trade_size(self):
        """Test case where candidate units are below minimum trade size."""
        # Scenario with very small balance and high minimum trade size
        balance = 10.0
        stop_loss_pips = 5.0
        pip_value = 0.0001
        current_price = 100.0  # High price instrument
        available_margin = 5.0  # Very limited margin
        margin_rate = 0.05  # Higher margin requirement
        minimum_trade_size = '1000'  # High minimum
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
        
        # Should return 0 units with reason mentioning minimum
        self.assertEqual(units, 0, "Should return 0 units when below minimum trade size")
        self.assertIn('reason', debug, "Debug should contain skip reason")
        self.assertIn('minimum', debug['reason'].lower(),
                     f"Reason should mention minimum: {debug['reason']}")
        
        print(f"\nBelow-minimum test:")
        print(f"  Reason: {debug['reason']}")
        print(f"  candidate_units: {debug.get('candidate_units', 0)}")
        print(f"  min_trade_size: {debug.get('min_trade_size', 0)}")
    
    def test_below_minimum_trade_value(self):
        """Test case where trade value is below MIN_TRADE_VALUE."""
        balance = 100.0
        stop_loss_pips = 10.0
        pip_value = 0.0001
        current_price = 0.01  # Very low price
        available_margin = 50.0
        margin_rate = 0.0333
        minimum_trade_size = '1'
        trade_units_precision = 0
        maximum_order_units = '100000000'
        risk_per_trade = 0.02
        max_units_per_instrument = 100000
        min_trade_value = 100.0  # High minimum trade value
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
        
        # Should return 0 units with reason about trade value
        self.assertEqual(units, 0, "Should return 0 units when below minimum trade value")
        self.assertIn('reason', debug, "Debug should contain skip reason")
        self.assertIn('trade value', debug['reason'].lower(),
                     f"Reason should mention trade value: {debug['reason']}")
        
        print(f"\nBelow-minimum-value test:")
        print(f"  Reason: {debug['reason']}")
        print(f"  trade_value: ${debug.get('trade_value', 0):.2f}")
    
    def test_successful_auto_scaling(self):
        """Test normal successful auto-scaling case."""
        balance = 1000.0
        stop_loss_pips = 10.0
        pip_value = 0.0001
        current_price = 1.2000
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
        
        # Should successfully compute units
        self.assertGreater(units, 0, "Should compute positive units")
        self.assertNotIn('reason', debug, "Should not have skip reason")
        
        # Verify risk is within limits
        self.assertLessEqual(risk_pct, risk_per_trade,
                            f"Risk {risk_pct*100:.2f}% should be <= {risk_per_trade*100:.2f}%")
        
        # Verify units respect both constraints
        self.assertLessEqual(units, debug['units_by_margin'],
                            "Units should not exceed margin constraint")
        self.assertLessEqual(units, debug['units_by_risk'],
                            "Units should not exceed risk constraint")
        
        print(f"\nSuccessful auto-scaling test:")
        print(f"  units_by_margin: {debug['units_by_margin']}")
        print(f"  units_by_risk: {debug['units_by_risk']}")
        print(f"  final units: {units}")
        print(f"  risk_pct: {risk_pct*100:.2f}%")
        print(f"  trade_value: ${debug['trade_value']:.2f}")
    
    def test_string_inputs_from_instrument_metadata(self):
        """Test that string inputs from instrument metadata are properly parsed."""
        # Scenario with all instrument metadata as strings (typical API response)
        balance = 1000.0
        stop_loss_pips = 10.0
        pip_value = 0.0001
        current_price = 1.1000
        available_margin = 900.0
        margin_rate = '0.0333'  # String from API
        minimum_trade_size = '1'  # String from API
        trade_units_precision = '0'  # String from API
        maximum_order_units = '100000000'  # String from API
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
        self.assertIsInstance(units, int, "Units should be an integer")
        
        print(f"\nString inputs test:")
        print(f"  margin_rate (string): '{margin_rate}'")
        print(f"  minimum_trade_size (string): '{minimum_trade_size}'")
        print(f"  final units: {units}")
        print(f"  risk_pct: {risk_pct*100:.2f}%")
    
    def test_invalid_string_inputs_handled_gracefully(self):
        """Test that invalid string inputs are handled without raising exceptions."""
        balance = 1000.0
        stop_loss_pips = 10.0
        pip_value = 0.0001
        current_price = 1.1000
        available_margin = 900.0
        margin_rate = 'invalid'  # Invalid string
        minimum_trade_size = 'abc'  # Invalid string
        trade_units_precision = 'xyz'  # Invalid string
        maximum_order_units = 'not_a_number'  # Invalid string
        risk_per_trade = 0.02
        max_units_per_instrument = 100000
        min_trade_value = 1.50
        margin_buffer = 0.5
        
        # Should not raise TypeError or ValueError
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
        
        # Should return 0 with a clear reason
        self.assertEqual(units, 0, "Should return 0 units for invalid inputs")
        self.assertIn('reason', debug, "Debug should contain skip reason")
        
        print(f"\nInvalid string inputs test:")
        print(f"  Reason: {debug['reason']}")
    
    def test_negative_inputs_handled(self):
        """Test that negative values are caught and handled."""
        balance = 1000.0
        stop_loss_pips = 10.0
        pip_value = 0.0001
        current_price = -1.1000  # Negative price (invalid)
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
        
        # Should return 0 with reason about invalid price
        self.assertEqual(units, 0, "Should return 0 units for negative price")
        self.assertIn('reason', debug, "Debug should contain skip reason")
        self.assertIn('price', debug['reason'].lower(), "Reason should mention price")
        
        print(f"\nNegative inputs test:")
        print(f"  Reason: {debug['reason']}")
    
    def test_zero_balance_handled(self):
        """Test that zero or negative balance is handled."""
        balance = 0.0  # Zero balance
        stop_loss_pips = 10.0
        pip_value = 0.0001
        current_price = 1.1000
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
        
        # Should return 0 with reason about invalid balance
        self.assertEqual(units, 0, "Should return 0 units for zero balance")
        self.assertIn('reason', debug, "Debug should contain skip reason")
        self.assertIn('balance', debug['reason'].lower(), "Reason should mention balance")
        
        print(f"\nZero balance test:")
        print(f"  Reason: {debug['reason']}")
    
    def test_real_world_usd_thb_scenario(self):
        """Test realistic USD_THB scenario with string metadata from API."""
        # Realistic USD_THB parameters
        balance = 100.0
        stop_loss_pips = 15.0
        pip_value = 0.01  # THB pairs typically have 0.01 pip value
        current_price = 33.5  # USD/THB around 33-34
        available_margin = 95.0
        margin_rate = '0.05'  # 20:1 leverage, string from API
        minimum_trade_size = '1'  # String from API
        trade_units_precision = '0'  # String from API
        maximum_order_units = '100000'  # String from API
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
        
        # Should either compute valid units or return 0 with clear reason
        self.assertIsInstance(units, int, "Units should be an integer")
        self.assertGreaterEqual(units, 0, "Units should be non-negative")
        
        if units == 0:
            self.assertIn('reason', debug, "Should have reason when units=0")
            print(f"\nUSD_THB test (skipped):")
            print(f"  Reason: {debug['reason']}")
        else:
            self.assertGreater(units, 0, "Units should be positive")
            print(f"\nUSD_THB test (executed):")
            print(f"  units: {units}")
            print(f"  risk_pct: {risk_pct*100:.2f}%")
            print(f"  trade_value: ${debug['trade_value']:.2f}")


if __name__ == '__main__':
    unittest.main()
