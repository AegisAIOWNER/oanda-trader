"""
Position sizing module implementing Kelly Criterion and fixed percentage methods.
"""
import logging
import numpy as np

class PositionSizer:
    """Calculate optimal position sizes based on various strategies."""
    
    def __init__(self, method='fixed_percentage', risk_per_trade=0.02, kelly_fraction=0.25):
        """
        Initialize position sizer.
        
        Args:
            method: 'fixed_percentage' or 'kelly_criterion'
            risk_per_trade: Fixed percentage of balance to risk (e.g., 0.02 = 2%)
            kelly_fraction: Fraction of Kelly Criterion to use (0.25 = quarter Kelly)
        """
        self.method = method
        self.risk_per_trade = risk_per_trade
        self.kelly_fraction = kelly_fraction
        
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
                               performance_metrics=None, confidence=1.0):
        """
        Calculate position size based on configured method.
        
        Args:
            balance: Account balance
            stop_loss_pips: Stop loss distance in pips
            pip_value: Value of 1 pip for the instrument
            performance_metrics: Optional dict with win_rate, avg_win, avg_loss
            confidence: Signal confidence (0.0 to 1.0)
            
        Returns:
            Tuple of (units, risk_percentage)
        """
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
            
            logging.info(f"Kelly position sizing: {units} units "
                        f"(risk: {adjusted_kelly*100:.2f}% of balance)")
            
            return units, adjusted_kelly
            
        else:
            # Use fixed percentage method
            units = self.calculate_fixed_percentage(balance, stop_loss_pips, pip_value)
            
            # Adjust by confidence
            adjusted_units = int(units * confidence)
            adjusted_units = max(100, adjusted_units)
            
            risk_pct = self.risk_per_trade * confidence
            
            logging.info(f"Fixed % position sizing: {adjusted_units} units "
                        f"(risk: {risk_pct*100:.2f}% of balance)")
            
            return adjusted_units, risk_pct
    
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
