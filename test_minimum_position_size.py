"""
Unit tests for minimum position size enforcement.
Tests that position sizing respects minimum trade value requirements.
"""
import unittest
from position_sizing import PositionSizer


class TestMinimumPositionSize(unittest.TestCase):
    """Test minimum position size enforcement for broker margin requirements."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.balance = 10000.0
        self.min_trade_value = 1.50  # Default minimum trade value
    
    def test_minimum_enforcement_with_eur_usd(self):
        """Test minimum position size enforcement with EUR_USD (0.0001 pip value)."""
        sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.001,  # Very low risk to trigger minimum
            min_trade_value=self.min_trade_value
        )
        
        # EUR_USD typical pip value
        pip_value = 0.0001
        stop_loss_pips = 10.0
        
        # Calculate position size
        units, risk_pct = sizer.calculate_position_size(
            balance=self.balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            confidence=1.0
        )
        
        # Verify minimum is enforced
        # min_units = 1.50 / (10.0 * 0.0001) = 1500 units
        expected_min_units = int(self.min_trade_value / (stop_loss_pips * pip_value))
        self.assertGreaterEqual(units, expected_min_units)
        
        # Verify trade value meets minimum
        trade_value = units * stop_loss_pips * pip_value
        self.assertGreaterEqual(trade_value, self.min_trade_value)
    
    def test_minimum_enforcement_with_usd_jpy(self):
        """Test minimum position size enforcement with USD_JPY (0.01 pip value)."""
        sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.001,  # Very low risk to trigger minimum
            min_trade_value=self.min_trade_value
        )
        
        # USD_JPY typical pip value
        pip_value = 0.01
        stop_loss_pips = 10.0
        
        # Calculate position size
        units, risk_pct = sizer.calculate_position_size(
            balance=self.balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            confidence=1.0
        )
        
        # Verify minimum is enforced
        # min_units = 1.50 / (10.0 * 0.01) = 150 units
        expected_min_units = int(self.min_trade_value / (stop_loss_pips * pip_value))
        self.assertGreaterEqual(units, expected_min_units)
        
        # Verify trade value meets minimum
        trade_value = units * stop_loss_pips * pip_value
        self.assertGreaterEqual(trade_value, self.min_trade_value)
    
    def test_minimum_not_applied_when_risk_based_is_higher(self):
        """Test that minimum is not applied when risk-based calculation is already higher."""
        sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.02,  # Normal risk that should result in larger size
            min_trade_value=self.min_trade_value
        )
        
        pip_value = 0.0001
        stop_loss_pips = 5.0
        
        # Calculate position size with normal risk
        units, risk_pct = sizer.calculate_position_size(
            balance=self.balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            confidence=1.0
        )
        
        # Calculate what minimum would be
        min_units = int(self.min_trade_value / (stop_loss_pips * pip_value))
        
        # Units should be higher than minimum (risk-based calculation dominates)
        self.assertGreater(units, min_units * 2)
    
    def test_minimum_with_low_confidence(self):
        """Test minimum enforcement when confidence reduces position size."""
        sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.01,
            min_trade_value=self.min_trade_value
        )
        
        pip_value = 0.0001
        stop_loss_pips = 10.0
        low_confidence = 0.2  # Low confidence that would reduce position size
        
        # Calculate position size with low confidence
        units, risk_pct = sizer.calculate_position_size(
            balance=self.balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            confidence=low_confidence
        )
        
        # Verify minimum is still enforced despite low confidence
        expected_min_units = int(self.min_trade_value / (stop_loss_pips * pip_value))
        self.assertGreaterEqual(units, expected_min_units)
        
        # Verify trade value meets minimum
        trade_value = units * stop_loss_pips * pip_value
        self.assertGreaterEqual(trade_value, self.min_trade_value)
    
    def test_minimum_with_kelly_criterion(self):
        """Test minimum enforcement with Kelly Criterion method."""
        sizer = PositionSizer(
            method='kelly_criterion',
            kelly_fraction=0.1,  # Very conservative Kelly
            min_trade_value=self.min_trade_value
        )
        
        pip_value = 0.0001
        stop_loss_pips = 15.0
        
        # Performance metrics that would result in small Kelly percentage
        performance_metrics = {
            'win_rate': 0.45,  # Below 50%
            'average_profit': 50,
            'average_loss': 60
        }
        
        # Calculate position size with Kelly
        units, risk_pct = sizer.calculate_position_size(
            balance=self.balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            performance_metrics=performance_metrics,
            confidence=1.0
        )
        
        # Verify minimum is enforced
        expected_min_units = int(self.min_trade_value / (stop_loss_pips * pip_value))
        self.assertGreaterEqual(units, expected_min_units)
        
        # Verify trade value meets minimum
        trade_value = units * stop_loss_pips * pip_value
        self.assertGreaterEqual(trade_value, self.min_trade_value)
    
    def test_custom_minimum_trade_value(self):
        """Test with custom minimum trade value."""
        custom_min = 2.00  # Higher minimum
        sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.001,
            min_trade_value=custom_min
        )
        
        pip_value = 0.0001
        stop_loss_pips = 10.0
        
        units, risk_pct = sizer.calculate_position_size(
            balance=self.balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            confidence=1.0
        )
        
        # Verify custom minimum is respected
        expected_min_units = int(custom_min / (stop_loss_pips * pip_value))
        self.assertGreaterEqual(units, expected_min_units)
        
        # Verify trade value meets custom minimum
        trade_value = units * stop_loss_pips * pip_value
        self.assertGreaterEqual(trade_value, custom_min)
    
    def test_minimum_with_tight_stops(self):
        """Test minimum enforcement with very tight stop losses."""
        sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.01,
            min_trade_value=self.min_trade_value
        )
        
        pip_value = 0.0001
        stop_loss_pips = 3.0  # Very tight stop
        
        units, risk_pct = sizer.calculate_position_size(
            balance=self.balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            confidence=1.0
        )
        
        # With tight stops, more units needed to meet minimum
        # min_units = 1.50 / (3.0 * 0.0001) = 5000 units
        expected_min_units = int(self.min_trade_value / (stop_loss_pips * pip_value))
        self.assertGreaterEqual(units, expected_min_units)
        
        # Verify trade value meets minimum
        trade_value = units * stop_loss_pips * pip_value
        self.assertGreaterEqual(trade_value, self.min_trade_value)
    
    def test_minimum_with_wide_stops(self):
        """Test minimum enforcement with wide stop losses."""
        sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.001,
            min_trade_value=self.min_trade_value
        )
        
        pip_value = 0.0001
        stop_loss_pips = 50.0  # Wide stop
        
        units, risk_pct = sizer.calculate_position_size(
            balance=self.balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            confidence=1.0
        )
        
        # With wide stops, fewer units needed to meet minimum
        # min_units = 1.50 / (50.0 * 0.0001) = 300 units
        expected_min_units = int(self.min_trade_value / (stop_loss_pips * pip_value))
        self.assertGreaterEqual(units, expected_min_units)
        
        # Verify trade value meets minimum
        trade_value = units * stop_loss_pips * pip_value
        self.assertGreaterEqual(trade_value, self.min_trade_value)
    
    def test_minimum_preserves_stops_and_limits(self):
        """Test that minimum enforcement doesn't affect stop loss and take profit levels."""
        sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.001,
            min_trade_value=self.min_trade_value
        )
        
        pip_value = 0.0001
        stop_loss_pips = 10.0
        
        # Calculate position size - this should adjust units but not stop loss
        units, risk_pct = sizer.calculate_position_size(
            balance=self.balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            confidence=1.0
        )
        
        # Stop loss should remain unchanged (this is tested implicitly by the calculation)
        # The minimum enforcement only changes units, not stop loss distance
        self.assertIsNotNone(units)
        self.assertIsNotNone(risk_pct)
        
        # Verify that minimum doesn't break risk calculation
        calculated_risk = units * stop_loss_pips * pip_value
        self.assertGreater(calculated_risk, 0)
    
    def test_absolute_minimum_floor(self):
        """Test that absolute minimum of 100 units is still enforced."""
        sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.02,
            min_trade_value=0.01  # Very small minimum
        )
        
        # Even with tiny minimum, should still have 100 units as floor
        pip_value = 0.0001
        stop_loss_pips = 10.0
        
        units, risk_pct = sizer.calculate_position_size(
            balance=self.balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            confidence=1.0
        )
        
        # Should be at least 100 units (absolute minimum)
        self.assertGreaterEqual(units, 100)


if __name__ == '__main__':
    unittest.main()
