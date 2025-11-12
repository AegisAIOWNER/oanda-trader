"""
Unit tests for auto-scaling position sizing.
Tests that position sizing auto-scales to fit available margin while respecting risk limits.
"""
import unittest
from position_sizing import PositionSizer


class TestAutoScaleUnits(unittest.TestCase):
    """Test auto-scaling position sizing for various scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.balance = 10000.0
        self.available_margin = 9000.0
        self.current_price = 1.1000
        self.stop_loss_pips = 10.0
        self.pip_value = 0.0001
        self.margin_rate = 0.0333  # ~30:1 leverage
        self.min_trade_value = 1.50
        
        self.sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.02,
            min_trade_value=self.min_trade_value
        )
    
    def test_margin_limited_scenario(self):
        """Test scenario where margin is the limiting factor."""
        # Set up scenario where margin allows fewer units than risk would
        balance = 10000.0
        available_margin = 1000.0  # Limited margin
        
        units, risk_pct, debug_info = self.sizer.calculate_auto_scaled_units(
            balance=balance,
            available_margin=available_margin,
            current_price=self.current_price,
            stop_loss_pips=self.stop_loss_pips,
            pip_value=self.pip_value,
            margin_rate=self.margin_rate,
            auto_scale_margin_buffer=0.0,
            minimum_trade_size=1,
            trade_units_precision=0,
            maximum_order_units=100000000,
            max_units_per_instrument=100000
        )
        
        # Should return valid units
        self.assertGreater(units, 0)
        
        # Units should be constrained by margin
        self.assertEqual(units, debug_info['units_by_margin'])
        
        # Risk percentage should be calculated
        self.assertGreater(risk_pct, 0)
        self.assertLess(risk_pct, 1.0)
    
    def test_risk_limited_scenario(self):
        """Test scenario where risk is the limiting factor."""
        # Set up scenario where risk allows fewer units than margin would
        balance = 10000.0
        available_margin = 50000.0  # Plenty of margin
        stop_loss_pips = 50.0  # Large SL means higher risk per unit
        
        units, risk_pct, debug_info = self.sizer.calculate_auto_scaled_units(
            balance=balance,
            available_margin=available_margin,
            current_price=self.current_price,
            stop_loss_pips=stop_loss_pips,
            pip_value=self.pip_value,
            margin_rate=self.margin_rate,
            auto_scale_margin_buffer=0.0,
            minimum_trade_size=1,
            trade_units_precision=0,
            maximum_order_units=100000000,
            max_units_per_instrument=100000
        )
        
        # Should return valid units
        self.assertGreater(units, 0)
        
        # Units should be constrained by risk
        self.assertLessEqual(units, debug_info['units_by_risk'])
        
        # Risk should be close to target (2%)
        self.assertLessEqual(risk_pct, 0.025)  # Allow some rounding error
    
    def test_margin_buffer_applied(self):
        """Test that margin buffer reduces available margin."""
        # Use smaller max limits to see the buffer effect
        max_units = 500000  # Higher limit
        
        # Test with 50% buffer
        units_with_buffer, _, debug_with_buffer = self.sizer.calculate_auto_scaled_units(
            balance=self.balance,
            available_margin=self.available_margin,
            current_price=self.current_price,
            stop_loss_pips=self.stop_loss_pips,
            pip_value=self.pip_value,
            margin_rate=self.margin_rate,
            auto_scale_margin_buffer=0.5,  # 50% buffer
            minimum_trade_size=1,
            trade_units_precision=0,
            maximum_order_units=max_units,
            max_units_per_instrument=max_units
        )
        
        # Test without buffer
        units_no_buffer, _, debug_no_buffer = self.sizer.calculate_auto_scaled_units(
            balance=self.balance,
            available_margin=self.available_margin,
            current_price=self.current_price,
            stop_loss_pips=self.stop_loss_pips,
            pip_value=self.pip_value,
            margin_rate=self.margin_rate,
            auto_scale_margin_buffer=0.0,  # No buffer
            minimum_trade_size=1,
            trade_units_precision=0,
            maximum_order_units=max_units,
            max_units_per_instrument=max_units
        )
        
        # Units with buffer should be less than without buffer
        # (unless both are risk-limited, in which case check effective margin)
        if debug_with_buffer['units_by_margin'] < debug_with_buffer['units_by_risk']:
            # Margin-limited case: buffer should reduce units
            self.assertLess(units_with_buffer, units_no_buffer)
        
        # Effective margin should be half with 50% buffer
        self.assertAlmostEqual(
            debug_with_buffer['effective_available_margin'],
            self.available_margin * 0.5,
            places=2
        )
    
    def test_instrument_minimum_enforced(self):
        """Test that instrument minimum trade size is enforced."""
        # Create scenario with very small calculated units
        balance = 100.0  # Small balance
        available_margin = 50.0  # Small margin
        minimum_trade_size = 1000  # Require 1000 units minimum
        
        units, risk_pct, result = self.sizer.calculate_auto_scaled_units(
            balance=balance,
            available_margin=available_margin,
            current_price=self.current_price,
            stop_loss_pips=self.stop_loss_pips,
            pip_value=self.pip_value,
            margin_rate=self.margin_rate,
            auto_scale_margin_buffer=0.0,
            minimum_trade_size=minimum_trade_size,
            trade_units_precision=0,
            maximum_order_units=100000000,
            max_units_per_instrument=100000
        )
        
        # Should return 0 units (skip trade)
        self.assertEqual(units, 0)
        
        # Should have skip reason
        self.assertIn('skip_reason', result)
        self.assertIn('minimum', result['skip_reason'].lower())
    
    def test_minimum_trade_value_enforced(self):
        """Test that minimum trade value is enforced."""
        # Create scenario where units * SL * pip_value < min_trade_value
        balance = 10000.0
        available_margin = 100.0  # Limited margin to force small units
        stop_loss_pips = 0.1  # Very tight SL
        
        units, risk_pct, result = self.sizer.calculate_auto_scaled_units(
            balance=balance,
            available_margin=available_margin,
            current_price=self.current_price,
            stop_loss_pips=stop_loss_pips,
            pip_value=self.pip_value,
            margin_rate=self.margin_rate,
            auto_scale_margin_buffer=0.0,
            minimum_trade_size=1,
            trade_units_precision=0,
            maximum_order_units=100000000,
            max_units_per_instrument=100000
        )
        
        # If units > 0, trade value should meet minimum
        if units > 0:
            trade_value = units * stop_loss_pips * self.pip_value
            self.assertGreaterEqual(trade_value, self.min_trade_value)
        else:
            # Otherwise should have skip reason
            self.assertIn('skip_reason', result)
    
    def test_rounding_to_precision(self):
        """Test that units are rounded to instrument precision."""
        # Test with whole units (precision 0)
        units_whole, _, _ = self.sizer.calculate_auto_scaled_units(
            balance=self.balance,
            available_margin=self.available_margin,
            current_price=self.current_price,
            stop_loss_pips=self.stop_loss_pips,
            pip_value=self.pip_value,
            margin_rate=self.margin_rate,
            auto_scale_margin_buffer=0.0,
            minimum_trade_size=1,
            trade_units_precision=0,  # Whole units
            maximum_order_units=100000000,
            max_units_per_instrument=100000
        )
        
        # Should be an integer
        self.assertEqual(units_whole, int(units_whole))
    
    def test_maximum_order_units_respected(self):
        """Test that maximum order units limit is respected."""
        maximum_order_units = 5000
        
        units, _, debug_info = self.sizer.calculate_auto_scaled_units(
            balance=self.balance,
            available_margin=self.available_margin,
            current_price=self.current_price,
            stop_loss_pips=self.stop_loss_pips,
            pip_value=self.pip_value,
            margin_rate=self.margin_rate,
            auto_scale_margin_buffer=0.0,
            minimum_trade_size=1,
            trade_units_precision=0,
            maximum_order_units=maximum_order_units,
            max_units_per_instrument=100000
        )
        
        # Units should not exceed maximum
        self.assertLessEqual(units, maximum_order_units)
    
    def test_max_units_per_instrument_respected(self):
        """Test that max units per instrument from config is respected."""
        max_units_per_instrument = 3000
        
        units, _, _ = self.sizer.calculate_auto_scaled_units(
            balance=self.balance,
            available_margin=self.available_margin,
            current_price=self.current_price,
            stop_loss_pips=self.stop_loss_pips,
            pip_value=self.pip_value,
            margin_rate=self.margin_rate,
            auto_scale_margin_buffer=0.0,
            minimum_trade_size=1,
            trade_units_precision=0,
            maximum_order_units=100000000,
            max_units_per_instrument=max_units_per_instrument
        )
        
        # Units should not exceed config maximum
        self.assertLessEqual(units, max_units_per_instrument)
    
    def test_zero_available_margin(self):
        """Test handling of zero available margin."""
        units, risk_pct, result = self.sizer.calculate_auto_scaled_units(
            balance=self.balance,
            available_margin=0.0,  # No margin
            current_price=self.current_price,
            stop_loss_pips=self.stop_loss_pips,
            pip_value=self.pip_value,
            margin_rate=self.margin_rate,
            auto_scale_margin_buffer=0.0,
            minimum_trade_size=1,
            trade_units_precision=0,
            maximum_order_units=100000000,
            max_units_per_instrument=100000
        )
        
        # Should return 0 units
        self.assertEqual(units, 0)
        
        # Should have skip reason
        self.assertIn('skip_reason', result)
        self.assertIn('margin', result['skip_reason'].lower())
    
    def test_invalid_price(self):
        """Test handling of invalid price."""
        units, risk_pct, result = self.sizer.calculate_auto_scaled_units(
            balance=self.balance,
            available_margin=self.available_margin,
            current_price=0.0,  # Invalid
            stop_loss_pips=self.stop_loss_pips,
            pip_value=self.pip_value,
            margin_rate=self.margin_rate,
            auto_scale_margin_buffer=0.0,
            minimum_trade_size=1,
            trade_units_precision=0,
            maximum_order_units=100000000,
            max_units_per_instrument=100000
        )
        
        # Should return 0 units
        self.assertEqual(units, 0)
        
        # Should have skip reason
        self.assertIn('skip_reason', result)
        self.assertIn('price', result['skip_reason'].lower())
    
    def test_acceptable_case(self):
        """Test a normal acceptable trading scenario."""
        units, risk_pct, debug_info = self.sizer.calculate_auto_scaled_units(
            balance=self.balance,
            available_margin=self.available_margin,
            current_price=self.current_price,
            stop_loss_pips=self.stop_loss_pips,
            pip_value=self.pip_value,
            margin_rate=self.margin_rate,
            auto_scale_margin_buffer=0.0,
            minimum_trade_size=1,
            trade_units_precision=0,
            maximum_order_units=100000000,
            max_units_per_instrument=100000
        )
        
        # Should return valid units
        self.assertGreater(units, 0)
        
        # Risk should be reasonable (not exceeding configured risk)
        self.assertGreater(risk_pct, 0)
        self.assertLessEqual(risk_pct, 0.03)  # Should be close to 2% with some buffer
        
        # Debug info should be populated
        self.assertIn('units_by_margin', debug_info)
        self.assertIn('units_by_risk', debug_info)
        self.assertIn('final_units', debug_info)
        self.assertIn('resulting_risk_pct', debug_info)
        
        # Final units should match returned units
        self.assertEqual(debug_info['final_units'], units)
    
    def test_debug_info_structure(self):
        """Test that debug info contains expected fields."""
        units, risk_pct, debug_info = self.sizer.calculate_auto_scaled_units(
            balance=self.balance,
            available_margin=self.available_margin,
            current_price=self.current_price,
            stop_loss_pips=self.stop_loss_pips,
            pip_value=self.pip_value,
            margin_rate=self.margin_rate,
            auto_scale_margin_buffer=0.0,
            minimum_trade_size=1,
            trade_units_precision=0,
            maximum_order_units=100000000,
            max_units_per_instrument=100000
        )
        
        # Required fields in debug info
        if units > 0:
            required_fields = [
                'effective_available_margin',
                'units_by_margin',
                'units_by_risk',
                'candidate_units_raw',
                'candidate_units_after_rounding',
                'min_trade_size',
                'trade_value',
                'final_units',
                'resulting_risk_pct',
                'actual_risk_amount',
                'required_margin_per_unit',
                'risk_amount',
                'risk_per_unit'
            ]
            
            for field in required_fields:
                self.assertIn(field, debug_info, f"Missing field: {field}")


if __name__ == '__main__':
    unittest.main()
