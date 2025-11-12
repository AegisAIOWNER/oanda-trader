"""
Position sizing module implementing Kelly Criterion and fixed percentage methods.
"""
import logging
import numpy as np

class PositionSizer:
    """Calculate optimal position sizes based on various strategies."""
    
    def __init__(self, method='fixed_percentage', risk_per_trade=0.02, kelly_fraction=0.25, min_trade_value=1.50):
        """
        Initialize position sizer.
        
        Args:
            method: 'fixed_percentage' or 'kelly_criterion'
            risk_per_trade: Fixed percentage of balance to risk (e.g., 0.02 = 2%)
            kelly_fraction: Fraction of Kelly Criterion to use (0.25 = quarter Kelly)
            min_trade_value: Minimum trade value in account currency (default: $1.50) to meet broker margin requirements
        """
        self.method = method
        self.risk_per_trade = risk_per_trade
        self.kelly_fraction = kelly_fraction
        self.min_trade_value = min_trade_value
        
    def calculate_kelly_criterion(self, win_rate, avg_win, avg_loss):
        """
        Calculate Kelly Criterion percentage.
        
        Kelly % = W - [(1 - W) / R]
        where W = win rate, R = reward/risk ratio
        
        Args:
            win_rate: Historical win rate (0.0 to 1.0)
            avg_win: Average winning trade amount
            avg_loss: Average losing trade amount (positive number)
            
        Returns:
            Kelly percentage (0.0 to 1.0)
        """
        if avg_loss == 0 or win_rate == 0:
            return 0.0
        
        # Calculate reward/risk ratio
        reward_risk_ratio = abs(avg_win / avg_loss)
        
        # Kelly formula
        kelly = win_rate - ((1 - win_rate) / reward_risk_ratio)
        
        # Apply Kelly fraction for safety (typically 0.25 to 0.5)
        fractional_kelly = kelly * self.kelly_fraction
        
        # Clamp between 0 and max risk
        kelly_clamped = max(0.0, min(fractional_kelly, self.risk_per_trade * 2))
        
        logging.debug(f"Kelly Criterion: win_rate={win_rate:.2f}, "
                     f"R/R={reward_risk_ratio:.2f}, kelly={kelly:.4f}, "
                     f"fractional={kelly_clamped:.4f}")
        
        return kelly_clamped
    
    def calculate_margin_based(self, balance, available_margin, current_price, margin_buffer=0.50, max_margin_usage=0.50):
        """
        Calculate position size based on available margin.
        
        This method calculates the maximum units that can be traded based on available margin,
        ensuring we don't exceed INSUFFICIENT_MARGIN errors for leveraged instruments.
        
        Args:
            balance: Account balance
            available_margin: Available margin from API
            current_price: Current price of the instrument
            margin_buffer: Minimum margin to keep available (default 0.50 = 50%)
            max_margin_usage: Maximum percentage of balance to use as margin (default 0.50 = 50%)
            
        Returns:
            Number of units to trade
        """
        if current_price <= 0:
            logging.warning("Invalid current price, using minimum position size")
            return 100
        
        # Calculate the maximum margin we're allowed to use
        # This respects both the margin buffer and max usage percentage
        max_allowed_margin = min(
            available_margin - (balance * margin_buffer),  # Leave margin_buffer % available
            balance * max_margin_usage  # Don't use more than max_margin_usage % of balance
        )
        
        # Ensure we don't go negative
        max_allowed_margin = max(0, max_allowed_margin)
        
        if max_allowed_margin <= 0:
            logging.warning("Insufficient margin available after applying buffer")
            return 100
        
        # For Oanda, margin required ≈ (units × price) / leverage
        # We don't know the exact leverage, so we use a conservative estimate
        # Assuming leverage of 50:1 for major pairs (worst case for margin requirement)
        # This means: margin_required = (units × price) / 50
        # Solving for units: units = (margin × 50) / price
        
        # Conservative leverage estimate (lower = more conservative)
        estimated_leverage = 20  # Conservative estimate for most instruments
        
        # Calculate maximum units based on available margin
        max_units = int((max_allowed_margin * estimated_leverage) / current_price)
        
        # Ensure minimum position size
        units = max(100, max_units)
        
        logging.debug(f"Margin-based sizing: balance={balance:.2f}, "
                     f"available_margin={available_margin:.2f}, "
                     f"max_allowed_margin={max_allowed_margin:.2f}, "
                     f"price={current_price:.5f}, units={units}")
        
        return units
    
    def calculate_fixed_percentage(self, balance, stop_loss_pips, pip_value=10):
        """
        Calculate position size using fixed percentage method.
        
        Position Size = (Account Balance × Risk %) / (Stop Loss in Pips × Pip Value)
        
        Args:
            balance: Account balance
            stop_loss_pips: Stop loss distance in pips
            pip_value: Value of 1 pip for the instrument (default 10 for standard lots)
            
        Returns:
            Number of units to trade
        """
        if stop_loss_pips == 0:
            logging.warning("Stop loss is 0, using minimum position size")
            return 1000
        
        # Calculate risk amount
        risk_amount = balance * self.risk_per_trade
        
        # Calculate position size
        units = int(risk_amount / (stop_loss_pips * pip_value))
        
        # Ensure minimum position size
        units = max(100, units)
        
        logging.debug(f"Fixed % sizing: balance={balance:.2f}, "
                     f"risk={self.risk_per_trade*100:.1f}%, "
                     f"risk_amount={risk_amount:.2f}, "
                     f"SL={stop_loss_pips:.4f} pips, units={units}")
        
        return units
    
    def calculate_position_size(self, balance, stop_loss_pips, pip_value=10, 
                               performance_metrics=None, confidence=1.0, 
                               available_margin=None, current_price=None, margin_buffer=0.50):
        """
        Calculate position size based on configured method.
        
        Args:
            balance: Account balance
            stop_loss_pips: Stop loss distance in pips
            pip_value: Value of 1 pip for the instrument
            performance_metrics: Optional dict with win_rate, avg_win, avg_loss
            confidence: Signal confidence (0.0 to 1.0)
            available_margin: Optional available margin from API (for margin-based sizing)
            current_price: Optional current instrument price (for margin-based sizing)
            margin_buffer: Margin buffer to maintain (default 0.50 = 50%)
            
        Returns:
            Tuple of (units, risk_percentage)
        """
        # If available_margin and current_price are provided, use margin-based sizing
        # This takes priority over other methods to prevent INSUFFICIENT_MARGIN errors
        if available_margin is not None and current_price is not None:
            logging.info("Using margin-based position sizing to prevent INSUFFICIENT_MARGIN errors")
            
            # Calculate position size based on available margin
            units = self.calculate_margin_based(
                balance=balance,
                available_margin=available_margin,
                current_price=current_price,
                margin_buffer=margin_buffer,
                max_margin_usage=0.50  # Use up to 50% of balance as per requirement
            )
            
            # Still enforce minimum position size for broker requirements
            units = self._enforce_minimum_position_size(units, pip_value, stop_loss_pips)
            
            # Calculate risk percentage for reporting
            # Risk = units × stop_loss_pips × pip_value
            risk_amount = units * stop_loss_pips * pip_value if stop_loss_pips > 0 else 0
            risk_pct = risk_amount / balance if balance > 0 else 0
            
            logging.info(f"Margin-based position sizing: {units} units "
                        f"(estimated risk: {risk_pct*100:.2f}% of balance)")
            
            return units, risk_pct
        
        # Fall back to original methods if margin info not available
        if self.method == 'kelly_criterion' and performance_metrics:
            # Use Kelly Criterion if we have performance data
            win_rate = performance_metrics.get('win_rate', 0.5)
            avg_win = performance_metrics.get('average_profit', 1.0)
            avg_loss = abs(performance_metrics.get('average_loss', -1.0))
            
            # Calculate Kelly percentage
            kelly_pct = self.calculate_kelly_criterion(win_rate, avg_win, avg_loss)
            
            # Adjust by confidence
            adjusted_kelly = kelly_pct * confidence
            
            # Calculate units based on Kelly percentage
            risk_amount = balance * adjusted_kelly
            units = int(risk_amount / (stop_loss_pips * pip_value)) if stop_loss_pips > 0 else 1000
            units = max(100, units)
            
            # Enforce minimum position size to meet broker margin requirements
            units = self._enforce_minimum_position_size(units, pip_value, stop_loss_pips)
            
            logging.info(f"Kelly position sizing: {units} units "
                        f"(risk: {adjusted_kelly*100:.2f}% of balance)")
            
            return units, adjusted_kelly
            
        else:
            # Use fixed percentage method
            units = self.calculate_fixed_percentage(balance, stop_loss_pips, pip_value)
            
            # Adjust by confidence
            adjusted_units = int(units * confidence)
            adjusted_units = max(100, adjusted_units)
            
            # Enforce minimum position size to meet broker margin requirements
            adjusted_units = self._enforce_minimum_position_size(adjusted_units, pip_value, stop_loss_pips)
            
            risk_pct = self.risk_per_trade * confidence
            
            logging.info(f"Fixed % position sizing: {adjusted_units} units "
                        f"(risk: {risk_pct*100:.2f}% of balance)")
            
            return adjusted_units, risk_pct
    
    def _enforce_minimum_position_size(self, units, pip_value, stop_loss_pips):
        """
        Enforce minimum position size based on minimum trade value.
        
        This ensures that the position meets broker margin requirements by calculating
        the minimum units needed to achieve the minimum trade value (e.g., $1-2).
        
        Args:
            units: Calculated position size in units
            pip_value: Value of 1 pip for the instrument (e.g., 0.0001 for EUR_USD, 0.01 for JPY pairs)
            stop_loss_pips: Stop loss distance in pips
            
        Returns:
            int: Adjusted units ensuring minimum trade value is met
        """
        if stop_loss_pips <= 0 or pip_value <= 0:
            logging.warning(f"Invalid parameters for minimum position size calculation: "
                          f"stop_loss_pips={stop_loss_pips}, pip_value={pip_value}")
            return max(100, units)
        
        # Calculate minimum units needed to achieve min_trade_value
        # Formula: min_units = min_trade_value / (stop_loss_pips * pip_value)
        # This ensures: min_units * stop_loss_pips * pip_value >= min_trade_value
        min_units = int(self.min_trade_value / (stop_loss_pips * pip_value))
        
        # Ensure at least 100 units as absolute minimum (legacy safeguard)
        min_units = max(100, min_units)
        
        if units < min_units:
            logging.info(f"Position size {units} units below minimum {min_units} units "
                        f"(required for ${self.min_trade_value:.2f} minimum trade value). "
                        f"Overriding to minimum size.")
            return min_units
        
        return units
    
    def get_recommended_method(self, total_trades):
        """
        Recommend position sizing method based on trading history.
        
        Args:
            total_trades: Number of trades in history
            
        Returns:
            Recommended method string
        """
        # Need at least 30 trades for Kelly to be reliable
        if total_trades < 30:
            return 'fixed_percentage'
        else:
            return 'kelly_criterion'
