"""
Unit tests for margin-based position sizing.
Tests that position sizing uses available margin to prevent INSUFFICIENT_MARGIN errors.
"""
import unittest
from position_sizing import PositionSizer


class TestMarginBasedSizing(unittest.TestCase):
    """Test margin-based position sizing for leveraged instruments."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.balance = 10000.0
        self.available_margin = 9000.0  # 90% available
        self.min_trade_value = 1.50
    
    def test_margin_based_calculation_eur_usd(self):
        """Test margin-based sizing with EUR_USD."""
        sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.02,
            min_trade_value=self.min_trade_value
        )
        
        current_price = 1.1000
        pip_value = 0.0001
        stop_loss_pips = 10.0
        
        # Calculate position size using margin-based approach
        units, risk_pct = sizer.calculate_position_size(
            balance=self.balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            confidence=1.0,
            available_margin=self.available_margin,
            current_price=current_price,
            margin_buffer=0.50
        )
        
        # Verify units are positive and reasonable
        self.assertGreater(units, 0)
        self.assertLess(units, 1000000)  # Sanity check
        
        # Verify risk percentage is calculated
        self.assertGreater(risk_pct, 0)
    
    def test_margin_based_with_buffer(self):
        """Test that margin buffer is respected."""
        sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.02,
            min_trade_value=self.min_trade_value
        )
        
        current_price = 1.3000
        pip_value = 0.0001
        stop_loss_pips = 15.0
        margin_buffer = 0.50  # Keep 50% margin available
        
        units, risk_pct = sizer.calculate_position_size(
            balance=self.balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            confidence=1.0,
            available_margin=self.available_margin,
            current_price=current_price,
            margin_buffer=margin_buffer
        )
        
        # Calculate implied margin usage
        # Using conservative leverage of 20:1
        estimated_leverage = 20
        implied_margin = (units * current_price) / estimated_leverage
        
        # Verify we're not using more than allowed
        # New formula: margin_buffer is a percentage of available margin to keep as buffer
        usable_margin = self.available_margin * (1 - margin_buffer)
        max_margin_from_balance = self.balance * 0.50  # max_margin_usage default
        max_allowed_margin = min(usable_margin, max_margin_from_balance)
        self.assertLessEqual(implied_margin, max_allowed_margin * 1.1)  # Allow 10% tolerance
    
    def test_margin_based_usd_jpy(self):
        """Test margin-based sizing with USD_JPY."""
        sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.02,
            min_trade_value=self.min_trade_value
        )
        
        current_price = 110.50
        pip_value = 0.01
        stop_loss_pips = 20.0
        
        units, risk_pct = sizer.calculate_position_size(
            balance=self.balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            confidence=1.0,
            available_margin=self.available_margin,
            current_price=current_price,
            margin_buffer=0.50
        )
        
        # Verify units are positive
        self.assertGreater(units, 0)
        
        # Verify minimum position size is enforced
        min_units = int(self.min_trade_value / (stop_loss_pips * pip_value))
        self.assertGreaterEqual(units, min_units)
    
    def test_margin_based_with_low_margin(self):
        """Test margin-based sizing with low available margin."""
        sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.02,
            min_trade_value=self.min_trade_value
        )
        
        # Very low available margin
        low_margin = 1000.0
        current_price = 1.2000
        pip_value = 0.0001
        stop_loss_pips = 10.0
        
        units, risk_pct = sizer.calculate_position_size(
            balance=self.balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            confidence=1.0,
            available_margin=low_margin,
            current_price=current_price,
            margin_buffer=0.50
        )
        
        # Should still return a valid position (minimum)
        self.assertGreaterEqual(units, 100)
    
    def test_margin_based_prevents_over_leverage(self):
        """Test that margin-based sizing prevents using too much margin."""
        sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.02,
            min_trade_value=self.min_trade_value
        )
        
        current_price = 1.1500
        pip_value = 0.0001
        stop_loss_pips = 12.0
        
        units, risk_pct = sizer.calculate_position_size(
            balance=self.balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            confidence=1.0,
            available_margin=self.available_margin,
            current_price=current_price,
            margin_buffer=0.50
        )
        
        # Calculate implied margin with conservative leverage
        estimated_leverage = 20
        implied_margin = (units * current_price) / estimated_leverage
        
        # Should not use more than 50% of balance
        max_usage = self.balance * 0.50
        self.assertLessEqual(implied_margin, max_usage * 1.1)  # Allow 10% tolerance
    
    def test_fallback_without_margin_info(self):
        """Test that system falls back to risk-based sizing without margin info."""
        sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.02,
            min_trade_value=self.min_trade_value
        )
        
        pip_value = 0.0001
        stop_loss_pips = 10.0
        
        # Call without margin info (should use risk-based calculation)
        units, risk_pct = sizer.calculate_position_size(
            balance=self.balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            confidence=1.0
            # No available_margin or current_price provided
        )
        
        # Should still return valid units
        self.assertGreater(units, 0)
        self.assertAlmostEqual(risk_pct, 0.02, delta=0.001)
    
    def test_margin_based_with_confidence_adjustment(self):
        """Test margin-based sizing with confidence adjustment."""
        sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.02,
            min_trade_value=self.min_trade_value
        )
        
        current_price = 1.2500
        pip_value = 0.0001
        stop_loss_pips = 15.0
        low_confidence = 0.5
        
        units, risk_pct = sizer.calculate_position_size(
            balance=self.balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            confidence=low_confidence,
            available_margin=self.available_margin,
            current_price=current_price,
            margin_buffer=0.50
        )
        
        # Should still work with confidence < 1.0
        self.assertGreater(units, 0)
        
        # Get units with full confidence for comparison
        units_full, _ = sizer.calculate_position_size(
            balance=self.balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            confidence=1.0,
            available_margin=self.available_margin,
            current_price=current_price,
            margin_buffer=0.50
        )
        
        # With margin-based sizing, units should be same (not affected by confidence)
        # because we're using available margin, not risk percentage
        self.assertEqual(units, units_full)
    
    def test_margin_calculation_function(self):
        """Test the calculate_margin_based method directly."""
        sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.02,
            min_trade_value=self.min_trade_value
        )
        
        current_price = 1.1000
        
        units = sizer.calculate_margin_based(
            balance=self.balance,
            available_margin=self.available_margin,
            current_price=current_price,
            margin_buffer=0.50,
            max_margin_usage=0.50
        )
        
        # Verify units are within reasonable range
        self.assertGreater(units, 100)
        self.assertLess(units, 1000000)
    
    def test_margin_based_with_high_price(self):
        """Test margin-based sizing with high price instrument."""
        sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.02,
            min_trade_value=self.min_trade_value
        )
        
        # High price like XAU_USD (gold)
        current_price = 1800.00
        pip_value = 0.01
        stop_loss_pips = 50.0
        
        units, risk_pct = sizer.calculate_position_size(
            balance=self.balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            confidence=1.0,
            available_margin=self.available_margin,
            current_price=current_price,
            margin_buffer=0.50
        )
        
        # Should handle high prices correctly
        self.assertGreater(units, 0)
        
        # Units should be smaller due to high price
        self.assertLess(units, 10000)
    
    def test_usd_sgd_leveraged_instrument(self):
        """Test margin-based sizing specifically for USD_SGD (high leverage instrument)."""
        sizer = PositionSizer(
            method='fixed_percentage',
            risk_per_trade=0.02,
            min_trade_value=self.min_trade_value
        )
        
        # USD_SGD typical scenario
        balance = 5000.0
        available_margin = 4500.0
        current_price = 1.3500
        pip_value = 0.0001
        stop_loss_pips = 20.0
        margin_buffer = 0.0  # Use all available margin (current config)
        
        units, risk_pct = sizer.calculate_position_size(
            balance=balance,
            stop_loss_pips=stop_loss_pips,
            pip_value=pip_value,
            confidence=1.0,
            available_margin=available_margin,
            current_price=current_price,
            margin_buffer=margin_buffer
        )
        
        # Should get valid position size
        self.assertGreater(units, 0)
        
        # With margin_buffer=0.0:
        # Usable margin = 4500 × (1 - 0.0) = 4500
        # Max from balance = 5000 × 0.50 = 2500
        # Max allowed margin = min(4500, 2500) = 2500
        # Max units = (2500 × 20) / 1.35 = ~37,037 units
        expected_max_units = 38000
        self.assertLessEqual(units, expected_max_units)
        
        # Verify we're using approximately 50% of balance as desired
        estimated_leverage = 20
        implied_margin = (units * current_price) / estimated_leverage
        self.assertLessEqual(implied_margin, balance * 0.55)  # Allow 5% tolerance
        self.assertGreaterEqual(implied_margin, balance * 0.45)  # Should be close to 50%


if __name__ == '__main__':
    unittest.main()
