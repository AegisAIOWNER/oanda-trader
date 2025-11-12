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
            margin_buffer: Percentage of available margin to keep as buffer (default 0.50 = 50%)
            max_margin_usage: Maximum percentage of balance to use as margin (default 0.50 = 50%)
            
        Returns:
            Number of units to trade
        """
        if current_price <= 0:
            logging.warning("Invalid current price, using minimum position size")
            return 100
        
        # Calculate the maximum margin we're allowed to use
        # margin_buffer is interpreted as a percentage of available margin to keep as safety buffer
        # For example, if margin_buffer=0.50, we use only 50% of available margin, keeping 50% as buffer
        usable_margin = available_margin * (1 - margin_buffer)
        
        # Don't use more than max_margin_usage % of balance (typically 50%)
        max_margin_from_balance = balance * max_margin_usage
        
        # Take the minimum of the two constraints
        max_allowed_margin = min(usable_margin, max_margin_from_balance)
        
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
    
    def calculate_auto_scaled_units(self, balance, stop_loss_pips, pip_value, 
                                     available_margin, current_price, margin_rate,
                                     minimum_trade_size, trade_units_precision,
                                     maximum_order_units, confidence=1.0,
                                     margin_buffer=0.0, min_units_override=None,
                                     max_units_per_instrument=100000):
        """
        Calculate auto-scaled position size that fits both margin and risk constraints.
        
        This method computes the maximum units that satisfy:
        - Available margin constraints (after buffer)
        - Risk-based position sizing
        - Broker minimum trade size
        - Instrument precision requirements
        - Maximum order units
        
        Args:
            balance: Account balance
            stop_loss_pips: Stop loss distance in pips
            pip_value: Value of 1 pip for the instrument
            available_margin: Available margin from API
            current_price: Current instrument price
            margin_rate: Margin rate for the instrument (e.g., 0.0333 for ~30:1 leverage)
            minimum_trade_size: Broker minimum trade size for this instrument
            trade_units_precision: Decimal precision for units (0 = integer)
            maximum_order_units: Broker maximum order units for this instrument
            confidence: Signal confidence (0.0 to 1.0)
            margin_buffer: Fraction of available margin to keep as buffer (0.0-1.0)
            min_units_override: Override for minimum units (None = use minimum_trade_size)
            max_units_per_instrument: Portfolio max units per instrument
            
        Returns:
            Tuple of (units, risk_percentage, reason)
            - units: Number of units to trade (0 if constraints not met)
            - risk_percentage: Actual risk as percentage of balance
            - reason: Explanation of sizing decision or skip reason
        """
        # a) Compute effective available margin
        effective_available_margin = max(0.0, available_margin * (1.0 - margin_buffer))
        
        # b) Calculate required margin per unit
        # Use fallback margin rate if missing
        if margin_rate is None or margin_rate <= 0:
            margin_rate = 0.0333  # Conservative default (~30:1 leverage)
            logging.debug(f"Using fallback margin_rate: {margin_rate}")
        
        required_margin_per_unit = current_price * margin_rate
        
        # c) Calculate units by margin
        if required_margin_per_unit > 0:
            units_by_margin = int(effective_available_margin / required_margin_per_unit)
        else:
            units_by_margin = 0
            logging.warning(f"Invalid required_margin_per_unit: {required_margin_per_unit}")
        
        # d) Calculate units by risk
        risk_amount = balance * self.risk_per_trade * confidence
        risk_per_unit = stop_loss_pips * pip_value
        
        if risk_per_unit > 0:
            units_by_risk = int(risk_amount / risk_per_unit)
        else:
            units_by_risk = 0
            logging.debug(f"Risk per unit is 0 or negative: {risk_per_unit}")
        
        # e) Calculate candidate units (take minimum of all constraints)
        candidate_units = min(
            units_by_margin,
            units_by_risk,
            maximum_order_units,
            max_units_per_instrument
        )
        
        # f) Round down to trade units precision
        if trade_units_precision == 0:
            candidate_units = int(candidate_units)
        else:
            # For non-zero precision, round to appropriate decimal places
            multiplier = 10 ** trade_units_precision
            candidate_units = int(candidate_units * multiplier) / multiplier
        
        # Determine effective minimum units
        effective_min_units = min_units_override if min_units_override is not None else minimum_trade_size
        
        # Check if candidate meets minimum trade size
        if candidate_units < effective_min_units:
            reason = f"Candidate units {candidate_units} < minimum {effective_min_units}"
            logging.info(f"Auto-scale skip: {reason}")
            return 0, 0.0, reason
        
        # Check if candidate meets minimum trade value
        trade_value = candidate_units * current_price
        if trade_value < self.min_trade_value:
            reason = f"Trade value ${trade_value:.2f} < minimum ${self.min_trade_value:.2f}"
            logging.info(f"Auto-scale skip: {reason}")
            return 0, 0.0, reason
        
        # Calculate actual risk percentage
        actual_risk_amount = candidate_units * stop_loss_pips * pip_value
        risk_pct = actual_risk_amount / balance if balance > 0 else 0.0
        
        # Log sizing details
        logging.debug(f"Auto-scale sizing: units_by_margin={units_by_margin}, "
                     f"units_by_risk={units_by_risk}, final_units={candidate_units}, "
                     f"minimum_trade_size={effective_min_units}, "
                     f"effective_available_margin={effective_available_margin:.2f}")
        
        reason = f"Scaled to {candidate_units} units (margin: {units_by_margin}, risk: {units_by_risk})"
        
        return candidate_units, risk_pct, reason
    
    def calculate_position_size(self, balance, stop_loss_pips, pip_value=10, 
                               performance_metrics=None, confidence=1.0, 
                               available_margin=None, current_price=None, margin_buffer=0.50,
                               enable_auto_scale=False, margin_rate=None,
                               minimum_trade_size=1, trade_units_precision=0,
                               maximum_order_units=100000000, auto_scale_margin_buffer=None,
                               auto_scale_min_units=None, max_units_per_instrument=100000):
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
            enable_auto_scale: Enable auto-scaling position sizing
            margin_rate: Margin rate for the instrument (for auto-scaling)
            minimum_trade_size: Broker minimum trade size (for auto-scaling)
            trade_units_precision: Decimal precision for units (for auto-scaling)
            maximum_order_units: Broker maximum order units (for auto-scaling)
            auto_scale_margin_buffer: Margin buffer for auto-scaling (overrides margin_buffer if set)
            auto_scale_min_units: Minimum units override for auto-scaling
            max_units_per_instrument: Portfolio max units per instrument
            
        Returns:
            Tuple of (units, risk_percentage) or (units, risk_percentage, reason) if auto-scaling
        """
        # Use auto-scaling if enabled and all required parameters are provided
        if enable_auto_scale and available_margin is not None and current_price is not None:
            logging.info("Using auto-scaling position sizing")
            
            # Use auto_scale_margin_buffer if provided, otherwise use margin_buffer
            effective_margin_buffer = auto_scale_margin_buffer if auto_scale_margin_buffer is not None else margin_buffer
            
            units, risk_pct, reason = self.calculate_auto_scaled_units(
                balance=balance,
                stop_loss_pips=stop_loss_pips,
                pip_value=pip_value,
                available_margin=available_margin,
                current_price=current_price,
                margin_rate=margin_rate,
                minimum_trade_size=minimum_trade_size,
                trade_units_precision=trade_units_precision,
                maximum_order_units=maximum_order_units,
                confidence=confidence,
                margin_buffer=effective_margin_buffer,
                min_units_override=auto_scale_min_units,
                max_units_per_instrument=max_units_per_instrument
            )
            
            logging.info(f"Auto-scaled position sizing: {units} units "
                        f"(risk: {risk_pct*100:.2f}% of balance) - {reason}")
            
            # Return tuple with reason for auto-scaling
            return units, risk_pct, reason
        
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
