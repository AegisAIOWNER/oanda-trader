"""
Integration test to verify margin-based position sizing works in bot context.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from position_sizing import PositionSizer
import pandas as pd


class TestMarginIntegration(unittest.TestCase):
    """Test margin-based position sizing integration with bot."""
    
    def test_position_sizing_with_margin_info(self):
        """Test that position sizer correctly uses margin information when provided."""
        # Setup
        sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.02,
            min_trade_value=1.50
        )
        
        # Simulate bot providing margin info
        balance = 10000.0
        available_margin = 9000.0
        current_price = 1.1000
        stop_loss_pips = 10.0
        pip_value = 0.0001
        margin_buffer = 0.50
        
        # Calculate position size with margin info
        units, risk_pct = sizer.calculate_position_size(
            balance=balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            confidence=1.0,
            available_margin=available_margin,
            current_price=current_price,
            margin_buffer=margin_buffer
        )
        
        # Verify we got valid results
        self.assertGreater(units, 0)
        self.assertGreater(risk_pct, 0)
        
        # Verify units are reasonable for the given margin
        # With 9000 available margin, 50% buffer (5000 reserved), and 20:1 leverage
        # Max allowed margin = 9000 - 5000 = 4000 (but also limited to 50% of balance = 5000)
        # So max_allowed_margin = min(4000, 5000) = 4000
        # Max units = (4000 * 20) / 1.1 = ~72,727 units
        self.assertLessEqual(units, 100000)  # Should be well under 100k
    
    def test_margin_sizing_vs_risk_sizing(self):
        """Compare margin-based sizing to traditional risk-based sizing."""
        sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.02,
            min_trade_value=1.50
        )
        
        balance = 10000.0
        stop_loss_pips = 10.0
        pip_value = 0.0001
        
        # Risk-based calculation (no margin info)
        units_risk, risk_pct_risk = sizer.calculate_position_size(
            balance=balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            confidence=1.0
        )
        
        # Margin-based calculation
        available_margin = 9000.0
        current_price = 1.1000
        units_margin, risk_pct_margin = sizer.calculate_position_size(
            balance=balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            confidence=1.0,
            available_margin=available_margin,
            current_price=current_price,
            margin_buffer=0.50
        )
        
        # Both should return valid units
        self.assertGreater(units_risk, 0)
        self.assertGreater(units_margin, 0)
        
        # Margin-based should typically be larger for leveraged instruments
        # (because it uses available margin, not just risk %)
        # However, both are valid approaches
        print(f"Risk-based units: {units_risk}, Margin-based units: {units_margin}")
    
    def test_insufficient_margin_scenario(self):
        """Test behavior when margin is very limited."""
        sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.02,
            min_trade_value=1.50
        )
        
        balance = 10000.0
        available_margin = 500.0  # Very low
        current_price = 1.2000
        stop_loss_pips = 15.0
        pip_value = 0.0001
        margin_buffer = 0.50
        
        # This should still work, just with smaller position
        units, risk_pct = sizer.calculate_position_size(
            balance=balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            confidence=1.0,
            available_margin=available_margin,
            current_price=current_price,
            margin_buffer=margin_buffer
        )
        
        # Should return minimum position size
        self.assertGreaterEqual(units, 100)
        
        # Units should be limited by low available margin
        self.assertLess(units, 10000)
    
    def test_high_leverage_instrument_sizing(self):
        """Test margin-based sizing for high leverage instruments like USD_SGD."""
        sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.02,
            min_trade_value=1.50
        )
        
        # Simulate USD_SGD scenario
        balance = 5000.0
        available_margin = 4500.0
        current_price = 1.3500  # USD_SGD typical price
        stop_loss_pips = 20.0
        pip_value = 0.0001
        margin_buffer = 0.50
        
        # Calculate position size
        units, risk_pct = sizer.calculate_position_size(
            balance=balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            confidence=1.0,
            available_margin=available_margin,
            current_price=current_price,
            margin_buffer=margin_buffer
        )
        
        # Verify we get valid units
        self.assertGreater(units, 0)
        
        # Verify the position respects margin constraints
        # New formula: margin_buffer is % of available margin to keep as buffer
        # Usable margin = 4500 × (1 - 0.50) = 2250
        # Max from balance = 5000 × 0.50 = 2500
        # Max allowed margin = min(2250, 2500) = 2250
        # Max units = (2250 * 20) / 1.35 = ~33,333 units
        estimated_max_units = 34000
        self.assertLessEqual(units, estimated_max_units)
        
        # Verify minimum is still enforced
        min_units = int(1.50 / (stop_loss_pips * pip_value))
        self.assertGreaterEqual(units, min_units)


if __name__ == '__main__':
    unittest.main()
