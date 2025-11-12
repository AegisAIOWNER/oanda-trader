"""
Integration test to verify auto-scaling position sizing works end-to-end.
This simulates a realistic trading scenario with actual margin constraints.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from position_sizing import PositionSizer


class TestAutoScaleIntegration(unittest.TestCase):
    """Integration tests for auto-scaling position sizing."""
    
    def test_realistic_forex_scenario(self):
        """Test auto-scaling with realistic forex trading parameters."""
        # Realistic account state
        balance = 5000.0
        available_margin = 4500.0
        
        # EUR/USD trading parameters
        current_price = 1.0850
        stop_loss_pips = 15.0
        pip_value = 0.0001
        margin_rate = 0.0333  # ~30:1 leverage
        
        # Instrument constraints from Oanda
        minimum_trade_size = 1
        trade_units_precision = 0
        maximum_order_units = 100000000
        max_units_per_instrument = 100000
        
        sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.02,  # 2% risk
            min_trade_value=1.50
        )
        
        # Calculate with auto-scaling
        units, risk_pct, debug_info = sizer.calculate_auto_scaled_units(
            balance=balance,
            available_margin=available_margin,
            current_price=current_price,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            margin_rate=margin_rate,
            auto_scale_margin_buffer=0.0,
            minimum_trade_size=minimum_trade_size,
            trade_units_precision=trade_units_precision,
            maximum_order_units=maximum_order_units,
            max_units_per_instrument=max_units_per_instrument
        )
        
        # Assertions
        self.assertGreater(units, 0, "Should calculate valid units")
        
        # Check risk is reasonable (close to 2%)
        self.assertGreater(risk_pct, 0.01, "Risk should be at least 1%")
        self.assertLess(risk_pct, 0.03, "Risk should not exceed 3%")
        
        # Check margin constraint is respected
        required_margin = units * current_price * margin_rate
        self.assertLessEqual(required_margin, available_margin, 
                            "Required margin should not exceed available")
        
        # Check minimum trade value is met
        trade_value = units * stop_loss_pips * pip_value
        self.assertGreaterEqual(trade_value, 1.50, 
                               "Trade value should meet minimum")
        
        # Log results
        print(f"\n✅ Realistic EUR/USD Scenario:")
        print(f"   Balance: ${balance:.2f}")
        print(f"   Available Margin: ${available_margin:.2f}")
        print(f"   Calculated Units: {units}")
        print(f"   Risk: {risk_pct*100:.2f}%")
        print(f"   Required Margin: ${required_margin:.2f}")
        print(f"   Trade Value: ${trade_value:.2f}")
    
    def test_small_account_scenario(self):
        """Test auto-scaling with a small account balance."""
        # Small account
        balance = 500.0
        available_margin = 450.0
        
        # GBP/USD with tighter stop
        current_price = 1.2650
        stop_loss_pips = 10.0
        pip_value = 0.0001
        margin_rate = 0.0333
        
        sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.02,
            min_trade_value=1.50
        )
        
        units, risk_pct, debug_info = sizer.calculate_auto_scaled_units(
            balance=balance,
            available_margin=available_margin,
            current_price=current_price,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            margin_rate=margin_rate,
            auto_scale_margin_buffer=0.0,
            minimum_trade_size=1,
            trade_units_precision=0,
            maximum_order_units=100000000,
            max_units_per_instrument=100000
        )
        
        # With small account, might skip trade
        if units == 0:
            # Should have a clear skip reason
            self.assertIn('skip_reason', debug_info)
            print(f"\n⚠️  Small Account Scenario:")
            print(f"   Balance: ${balance:.2f}")
            print(f"   Available Margin: ${available_margin:.2f}")
            print(f"   Skip Reason: {debug_info['skip_reason']}")
        else:
            # If trade is possible, verify constraints
            self.assertGreater(units, 0)
            trade_value = units * stop_loss_pips * pip_value
            self.assertGreaterEqual(trade_value, 1.50)
            
            print(f"\n✅ Small Account Scenario:")
            print(f"   Balance: ${balance:.2f}")
            print(f"   Calculated Units: {units}")
            print(f"   Risk: {risk_pct*100:.2f}%")
            print(f"   Trade Value: ${trade_value:.2f}")
    
    def test_high_leverage_instrument(self):
        """Test with high leverage instrument (lower margin requirements)."""
        # Account state
        balance = 10000.0
        available_margin = 9000.0
        
        # Major pair with high leverage
        current_price = 1.0950
        stop_loss_pips = 20.0
        pip_value = 0.0001
        margin_rate = 0.02  # 50:1 leverage (lower margin requirement)
        
        sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.02,
            min_trade_value=1.50
        )
        
        units, risk_pct, debug_info = sizer.calculate_auto_scaled_units(
            balance=balance,
            available_margin=available_margin,
            current_price=current_price,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            margin_rate=margin_rate,
            auto_scale_margin_buffer=0.0,
            minimum_trade_size=1,
            trade_units_precision=0,
            maximum_order_units=100000000,
            max_units_per_instrument=100000
        )
        
        # Should calculate valid units
        self.assertGreater(units, 0)
        
        # With high leverage, should be risk-limited rather than margin-limited
        # (risk constraint should be tighter than margin constraint)
        units_by_margin = debug_info['units_by_margin']
        units_by_risk = debug_info['units_by_risk']
        
        print(f"\n✅ High Leverage Scenario:")
        print(f"   Margin Rate: {margin_rate} (leverage: {1/margin_rate:.0f}:1)")
        print(f"   Units by Margin: {units_by_margin}")
        print(f"   Units by Risk: {units_by_risk}")
        print(f"   Final Units: {units} ({'risk-limited' if units == units_by_risk else 'margin-limited'})")
    
    def test_with_margin_buffer(self):
        """Test auto-scaling with margin buffer for safety."""
        balance = 10000.0
        available_margin = 9000.0
        current_price = 1.1000
        stop_loss_pips = 15.0
        pip_value = 0.0001
        margin_rate = 0.0333
        
        sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.02,
            min_trade_value=1.50
        )
        
        # Calculate with 50% buffer
        units_buffered, risk_buffered, debug_buffered = sizer.calculate_auto_scaled_units(
            balance=balance,
            available_margin=available_margin,
            current_price=current_price,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            margin_rate=margin_rate,
            auto_scale_margin_buffer=0.5,  # 50% buffer
            minimum_trade_size=1,
            trade_units_precision=0,
            maximum_order_units=100000000,
            max_units_per_instrument=100000
        )
        
        # Calculate without buffer
        units_no_buffer, risk_no_buffer, debug_no_buffer = sizer.calculate_auto_scaled_units(
            balance=balance,
            available_margin=available_margin,
            current_price=current_price,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            margin_rate=margin_rate,
            auto_scale_margin_buffer=0.0,  # No buffer
            minimum_trade_size=1,
            trade_units_precision=0,
            maximum_order_units=100000000,
            max_units_per_instrument=100000
        )
        
        print(f"\n✅ Margin Buffer Comparison:")
        print(f"   No Buffer - Units: {units_no_buffer}, Effective Margin: ${debug_no_buffer['effective_available_margin']:.2f}")
        print(f"   50% Buffer - Units: {units_buffered}, Effective Margin: ${debug_buffered['effective_available_margin']:.2f}")
        print(f"   Reduction: {((units_no_buffer - units_buffered) / units_no_buffer * 100):.1f}% fewer units with buffer")
        
        # Verify buffer is applied correctly
        self.assertAlmostEqual(
            debug_buffered['effective_available_margin'],
            available_margin * 0.5,
            places=2
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)
