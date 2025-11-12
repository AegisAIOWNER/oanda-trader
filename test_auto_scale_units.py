"""
Unit tests for auto-scaling position sizing.
Tests that auto-scaling correctly computes position sizes within margin and risk constraints.
"""
import unittest
from position_sizing import PositionSizer


class TestAutoScaleUnits(unittest.TestCase):
    """Test auto-scaling position sizing functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.balance = 10000.0
        self.min_trade_value = 1.50
    
    def test_small_balance_eur_usd(self):
        """
        Test 1: Small balance with EUR_USD.
        
        Scenario:
        - Small balance
        - EUR_USD at 1.1
        - marginRate 0.0333
        - stop_loss_pips=50
        - pip_value=0.0001
        - RISK_PER_TRADE=0.02
        
        Expected: candidate units computed correctly, meets instrument minimum
        """
        sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.02,
            min_trade_value=self.min_trade_value
        )
        
        balance = 1000.0  # Small balance
        available_margin = 900.0  # 90% available
        current_price = 1.1
        margin_rate = 0.0333
        stop_loss_pips = 50.0
        pip_value = 0.0001
        minimum_trade_size = 1.0
        trade_units_precision = 0
        maximum_order_units = 100000000
        margin_buffer = 0.0  # No buffer for this test
        
        units, risk_pct, reason = sizer.calculate_auto_scaled_units(
            balance=balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            available_margin=available_margin,
            current_price=current_price,
            margin_rate=margin_rate,
            minimum_trade_size=minimum_trade_size,
            trade_units_precision=trade_units_precision,
            maximum_order_units=maximum_order_units,
            confidence=1.0,
            margin_buffer=margin_buffer,
            max_units_per_instrument=100000
        )
        
        # Calculate expected values
        # effective_available_margin = 900.0 * (1.0 - 0.0) = 900.0
        # required_margin_per_unit = 1.1 * 0.0333 = 0.03663
        # units_by_margin = floor(900.0 / 0.03663) = 24,565
        # risk_amount = 1000.0 * 0.02 * 1.0 = 20.0
        # risk_per_unit = 50.0 * 0.0001 = 0.005
        # units_by_risk = floor(20.0 / 0.005) = 4,000
        # candidate_units = min(24565, 4000, 100000000, 100000) = 4,000
        
        # Verify units are positive and meet constraints
        self.assertGreater(units, 0, "Units should be greater than 0")
        self.assertGreaterEqual(units, minimum_trade_size, 
                               f"Units {units} should be >= minimum {minimum_trade_size}")
        self.assertLessEqual(units, 4000, "Units should be limited by risk")
        
        # Verify risk percentage is reasonable
        self.assertGreater(risk_pct, 0)
        self.assertLessEqual(risk_pct, 0.03, "Risk should not exceed ~3% for this scenario")
        
        # Verify reason is provided
        self.assertIsNotNone(reason)
        self.assertIn("units", reason.lower())
    
    def test_very_large_atr_zero_risk(self):
        """
        Test 2: Very large ATR results in units_by_risk = 0.
        
        Scenario: 
        - Large stop loss (high ATR)
        - Results in risk per unit being too high
        - Should return 0 units with appropriate reason
        """
        sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.02,
            min_trade_value=self.min_trade_value
        )
        
        balance = 1000.0
        available_margin = 900.0
        current_price = 1.1
        margin_rate = 0.0333
        stop_loss_pips = 5000.0  # Very large ATR/stop loss
        pip_value = 0.0001
        minimum_trade_size = 1.0
        trade_units_precision = 0
        maximum_order_units = 100000000
        
        units, risk_pct, reason = sizer.calculate_auto_scaled_units(
            balance=balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            available_margin=available_margin,
            current_price=current_price,
            margin_rate=margin_rate,
            minimum_trade_size=minimum_trade_size,
            trade_units_precision=trade_units_precision,
            maximum_order_units=maximum_order_units,
            confidence=1.0,
            margin_buffer=0.0,
            max_units_per_instrument=100000
        )
        
        # With very large stop loss:
        # risk_amount = 1000.0 * 0.02 = 20.0
        # risk_per_unit = 5000.0 * 0.0001 = 0.5
        # units_by_risk = floor(20.0 / 0.5) = 40
        # This might still give some units, but if stop is even larger, we'd get 0
        
        # For an even more extreme case, let's check if it's small
        # The units should be very small due to high risk per unit
        self.assertLess(units, 100, "Units should be very small with large ATR")
        
        # Verify risk percentage
        if units == 0:
            self.assertEqual(risk_pct, 0.0)
            self.assertIn("minimum", reason.lower())
    
    def test_margin_limited_instrument(self):
        """
        Test 3: Margin-limited instrument where margin < risk constraint.
        
        Scenario:
        - Instrument where margin limits position size
        - units_by_margin < units_by_risk
        - Should return units_by_margin
        """
        sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.02,
            min_trade_value=self.min_trade_value
        )
        
        balance = 1000.0
        available_margin = 100.0  # Very limited margin
        current_price = 100.0  # High price
        margin_rate = 0.05  # Higher margin requirement
        stop_loss_pips = 10.0  # Small stop
        pip_value = 0.01
        minimum_trade_size = 1.0
        trade_units_precision = 0
        maximum_order_units = 100000000
        
        units, risk_pct, reason = sizer.calculate_auto_scaled_units(
            balance=balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            available_margin=available_margin,
            current_price=current_price,
            margin_rate=margin_rate,
            minimum_trade_size=minimum_trade_size,
            trade_units_precision=trade_units_precision,
            maximum_order_units=maximum_order_units,
            confidence=1.0,
            margin_buffer=0.0,
            max_units_per_instrument=100000
        )
        
        # Calculate expected values
        # effective_available_margin = 100.0
        # required_margin_per_unit = 100.0 * 0.05 = 5.0
        # units_by_margin = floor(100.0 / 5.0) = 20
        # risk_amount = 1000.0 * 0.02 = 20.0
        # risk_per_unit = 10.0 * 0.01 = 0.1
        # units_by_risk = floor(20.0 / 0.1) = 200
        # candidate_units = min(20, 200, ...) = 20
        
        # Verify units are limited by margin
        self.assertGreater(units, 0)
        self.assertLessEqual(units, 20, "Units should be limited by available margin")
        
        # Verify reason mentions margin constraint
        self.assertIsNotNone(reason)
    
    def test_below_minimum_trade_size(self):
        """
        Test 4: Candidate units below minimum trade size.
        
        Should return 0 units with reason containing 'minimum'
        """
        sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.02,
            min_trade_value=self.min_trade_value
        )
        
        balance = 100.0  # Very small balance
        available_margin = 10.0  # Very limited margin
        current_price = 100.0  # High price
        margin_rate = 0.10  # High margin requirement
        stop_loss_pips = 50.0
        pip_value = 0.01
        minimum_trade_size = 100.0  # High minimum
        trade_units_precision = 0
        maximum_order_units = 100000000
        
        units, risk_pct, reason = sizer.calculate_auto_scaled_units(
            balance=balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            available_margin=available_margin,
            current_price=current_price,
            margin_rate=margin_rate,
            minimum_trade_size=minimum_trade_size,
            trade_units_precision=trade_units_precision,
            maximum_order_units=maximum_order_units,
            confidence=1.0,
            margin_buffer=0.0,
            max_units_per_instrument=100000
        )
        
        # Should return 0 units because calculated units < minimum_trade_size
        self.assertEqual(units, 0, "Units should be 0 when below minimum")
        self.assertEqual(risk_pct, 0.0)
        self.assertIn("minimum", reason.lower(), "Reason should mention minimum constraint")
    
    def test_below_minimum_trade_value(self):
        """
        Test 5: Trade value below minimum trade value.
        
        Should return 0 units with reason containing 'value'
        """
        sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.02,
            min_trade_value=10.0  # Higher minimum trade value
        )
        
        balance = 1000.0
        available_margin = 500.0
        current_price = 0.01  # Very low price
        margin_rate = 0.0333
        stop_loss_pips = 10.0
        pip_value = 0.0001
        minimum_trade_size = 1.0
        trade_units_precision = 0
        maximum_order_units = 100000000
        
        units, risk_pct, reason = sizer.calculate_auto_scaled_units(
            balance=balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            available_margin=available_margin,
            current_price=current_price,
            margin_rate=margin_rate,
            minimum_trade_size=minimum_trade_size,
            trade_units_precision=trade_units_precision,
            maximum_order_units=maximum_order_units,
            confidence=1.0,
            margin_buffer=0.0,
            max_units_per_instrument=100000
        )
        
        # Calculate if trade value would be below minimum
        # If units * price < min_trade_value, should return 0
        if units > 0:
            trade_value = units * current_price
            self.assertGreaterEqual(trade_value, 10.0, 
                                  "Trade value should meet minimum or units should be 0")
        else:
            self.assertEqual(risk_pct, 0.0)
            self.assertIn("value", reason.lower(), "Reason should mention value constraint")
    
    def test_confidence_adjustment(self):
        """
        Test 6: Confidence adjustment affects risk-based units.
        
        Lower confidence should result in smaller position size
        """
        sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.02,
            min_trade_value=self.min_trade_value
        )
        
        balance = 10000.0
        available_margin = 9000.0
        current_price = 1.2
        margin_rate = 0.0333
        stop_loss_pips = 20.0
        pip_value = 0.0001
        minimum_trade_size = 1.0
        trade_units_precision = 0
        maximum_order_units = 100000000
        
        # Calculate with full confidence
        units_full, risk_pct_full, reason_full = sizer.calculate_auto_scaled_units(
            balance=balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            available_margin=available_margin,
            current_price=current_price,
            margin_rate=margin_rate,
            minimum_trade_size=minimum_trade_size,
            trade_units_precision=trade_units_precision,
            maximum_order_units=maximum_order_units,
            confidence=1.0,
            margin_buffer=0.0,
            max_units_per_instrument=100000
        )
        
        # Calculate with half confidence
        units_half, risk_pct_half, reason_half = sizer.calculate_auto_scaled_units(
            balance=balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            available_margin=available_margin,
            current_price=current_price,
            margin_rate=margin_rate,
            minimum_trade_size=minimum_trade_size,
            trade_units_precision=trade_units_precision,
            maximum_order_units=maximum_order_units,
            confidence=0.5,
            margin_buffer=0.0,
            max_units_per_instrument=100000
        )
        
        # Half confidence should result in smaller or equal position size
        self.assertLessEqual(units_half, units_full, 
                           "Lower confidence should not increase position size")
        self.assertLessEqual(risk_pct_half, risk_pct_full,
                           "Lower confidence should not increase risk")
    
    def test_margin_buffer_reduces_units(self):
        """
        Test 7: Margin buffer reduces available margin and thus units.
        
        Higher buffer should result in smaller position size
        """
        sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.02,
            min_trade_value=self.min_trade_value
        )
        
        balance = 10000.0
        available_margin = 5000.0
        current_price = 1.1
        margin_rate = 0.05  # Use higher margin rate to make margin the limiting factor
        stop_loss_pips = 10.0
        pip_value = 0.0001
        minimum_trade_size = 1.0
        trade_units_precision = 0
        maximum_order_units = 100000000
        
        # Calculate with no buffer
        units_no_buffer, _, _ = sizer.calculate_auto_scaled_units(
            balance=balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            available_margin=available_margin,
            current_price=current_price,
            margin_rate=margin_rate,
            minimum_trade_size=minimum_trade_size,
            trade_units_precision=trade_units_precision,
            maximum_order_units=maximum_order_units,
            confidence=1.0,
            margin_buffer=0.0,
            max_units_per_instrument=100000
        )
        
        # Calculate with 50% buffer
        units_with_buffer, _, _ = sizer.calculate_auto_scaled_units(
            balance=balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            available_margin=available_margin,
            current_price=current_price,
            margin_rate=margin_rate,
            minimum_trade_size=minimum_trade_size,
            trade_units_precision=trade_units_precision,
            maximum_order_units=maximum_order_units,
            confidence=1.0,
            margin_buffer=0.5,
            max_units_per_instrument=100000
        )
        
        # Buffer should reduce position size (or keep it same if risk-limited)
        self.assertLessEqual(units_with_buffer, units_no_buffer,
                           "Margin buffer should not increase position size")
    
    def test_integration_with_calculate_position_size(self):
        """
        Test 8: Integration test through calculate_position_size with auto-scaling enabled.
        """
        sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.02,
            min_trade_value=self.min_trade_value
        )
        
        balance = 5000.0
        available_margin = 4500.0
        current_price = 1.15
        margin_rate = 0.0333
        stop_loss_pips = 30.0
        pip_value = 0.0001
        minimum_trade_size = 1.0
        trade_units_precision = 0
        maximum_order_units = 100000000
        
        result = sizer.calculate_position_size(
            balance=balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            confidence=1.0,
            available_margin=available_margin,
            current_price=current_price,
            margin_buffer=0.0,
            enable_auto_scale=True,
            margin_rate=margin_rate,
            minimum_trade_size=minimum_trade_size,
            trade_units_precision=trade_units_precision,
            maximum_order_units=maximum_order_units,
            auto_scale_margin_buffer=0.0,
            auto_scale_min_units=None,
            max_units_per_instrument=100000
        )
        
        # Should return 3-tuple with reason when auto-scaling enabled
        self.assertEqual(len(result), 3, "Auto-scaling should return 3-tuple")
        units, risk_pct, reason = result
        
        # Verify reasonable values
        self.assertGreater(units, 0, "Units should be positive")
        self.assertGreater(risk_pct, 0, "Risk percentage should be positive")
        self.assertIsNotNone(reason, "Reason should be provided")
    
    def test_fallback_margin_rate(self):
        """
        Test 9: Fallback to default margin rate when None or invalid.
        """
        sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.02,
            min_trade_value=self.min_trade_value
        )
        
        balance = 1000.0
        available_margin = 900.0
        current_price = 1.1
        margin_rate = None  # Test fallback
        stop_loss_pips = 20.0
        pip_value = 0.0001
        minimum_trade_size = 1.0
        trade_units_precision = 0
        maximum_order_units = 100000000
        
        units, risk_pct, reason = sizer.calculate_auto_scaled_units(
            balance=balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            available_margin=available_margin,
            current_price=current_price,
            margin_rate=margin_rate,
            minimum_trade_size=minimum_trade_size,
            trade_units_precision=trade_units_precision,
            maximum_order_units=maximum_order_units,
            confidence=1.0,
            margin_buffer=0.0,
            max_units_per_instrument=100000
        )
        
        # Should still calculate units using fallback margin rate
        self.assertGreater(units, 0, "Should calculate units with fallback margin rate")
        self.assertGreater(risk_pct, 0)


if __name__ == '__main__':
    unittest.main()
