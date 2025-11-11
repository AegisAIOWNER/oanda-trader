"""
Adaptive Threshold Manager - Makes the bot autonomously adjust confidence threshold
based on performance and signal frequency, enabling AI-like self-optimization.
"""
import logging
from datetime import datetime


class AdaptiveThresholdManager:
    """
    Manages dynamic adjustment of CONFIDENCE_THRESHOLD based on:
    1. Signal frequency - lowers threshold if no signals found for several cycles
    2. Performance tracking - adjusts based on win/loss profitability
    3. Self-learning - stores decisions and reasoning in database
    """
    
    def __init__(self, base_threshold=0.8, db=None, 
                 min_threshold=0.5, max_threshold=0.95,
                 no_signal_cycles_trigger=5, adjustment_step=0.02,
                 volatility_detector=None):
        """
        Initialize adaptive threshold manager.
        
        Args:
            base_threshold: Initial threshold value from config
            db: TradeDatabase instance for storing decisions
            min_threshold: Minimum allowed threshold (safety floor)
            max_threshold: Maximum allowed threshold (safety ceiling)
            no_signal_cycles_trigger: Cycles without signals before lowering threshold
            adjustment_step: Amount to adjust threshold by (e.g., 0.02 = 2%)
            volatility_detector: Optional VolatilityDetector instance for volatility-aware adjustments
        """
        self.base_threshold = base_threshold
        self.min_threshold = min_threshold
        self.max_threshold = max_threshold
        self.no_signal_cycles_trigger = no_signal_cycles_trigger
        self.adjustment_step = adjustment_step
        self.db = db
        self.volatility_detector = volatility_detector
        
        # Load last threshold from database if available, otherwise use base threshold
        last_threshold = None
        if self.db:
            last_threshold = self.db.get_last_threshold()
        
        if last_threshold is not None:
            # Ensure loaded threshold is within bounds
            self.current_threshold = max(min_threshold, min(max_threshold, last_threshold))
            logging.info(f"Adaptive threshold loaded from database: {self.current_threshold:.3f}")
        else:
            self.current_threshold = base_threshold
            logging.info(f"Adaptive threshold initialized with base value: {base_threshold:.3f}")
        
        # Tracking state
        self.cycles_without_signal = 0
        self.last_adjustment_time = datetime.now()
        
        logging.info(f"Adaptive threshold initialized: current={self.current_threshold:.3f}, "
                     f"base={base_threshold:.3f}, range=[{min_threshold:.3f}, {max_threshold:.3f}]")
    
    def update_on_cycle(self, signals_found):
        """
        Update threshold based on whether signals were found in this cycle.
        
        Args:
            signals_found: Number of signals found in the current cycle
            
        Returns:
            bool: True if threshold was adjusted
        """
        if signals_found > 0:
            # Reset counter when signals are found
            self.cycles_without_signal = 0
            return False
        
        # Increment counter when no signals found
        self.cycles_without_signal += 1
        
        # Check if we need to lower threshold
        if self.cycles_without_signal >= self.no_signal_cycles_trigger:
            return self._lower_threshold_for_signal_frequency()
        
        return False
    
    def _lower_threshold_for_signal_frequency(self):
        """Lower threshold due to lack of signals."""
        old_threshold = self.current_threshold
        
        # Get volatility-adjusted step if volatility detector is available
        adjustment_step = self.adjustment_step
        if self.volatility_detector:
            vol_adjustment = self.volatility_detector.get_threshold_adjustment(
                self.current_threshold, self.adjustment_step
            )
            adjustment_step = vol_adjustment['adjusted_step']
            logging.info(f"🌡️ VOLATILITY-AWARE ADJUSTMENT: Using step={adjustment_step:.4f} "
                        f"(base={self.adjustment_step:.4f})")
        
        new_threshold = max(self.min_threshold, 
                           self.current_threshold - adjustment_step)
        
        if new_threshold < old_threshold:
            self.current_threshold = new_threshold
            self.cycles_without_signal = 0  # Reset counter
            
            reason = (f"Lowered threshold after {self.no_signal_cycles_trigger} cycles "
                     f"without signals to increase signal frequency")
            
            # Add volatility context if available
            if self.volatility_detector:
                vol_state = self.volatility_detector.current_volatility_state
                avg_atr = self.volatility_detector.current_avg_atr
                reason += (f" [Volatility: {vol_state}, avg_atr={avg_atr:.6f}, "
                          f"adjustment_step={adjustment_step:.4f}]")
            
            self._log_adjustment(old_threshold, new_threshold, reason,
                               cycles_without_signal=self.no_signal_cycles_trigger)
            return True
        
        return False
    
    def update_on_trade_result(self, trade_profitable, recent_performance=None):
        """
        Update threshold based on trade outcome and recent performance.
        
        Args:
            trade_profitable: bool - whether the trade was profitable
            recent_performance: dict with 'win_rate', 'profit_factor', 'total_trades'
            
        Returns:
            bool: True if threshold was adjusted
        """
        if recent_performance is None or recent_performance.get('total_trades', 0) < 5:
            # Need minimum trade history for performance-based adjustments
            return False
        
        win_rate = recent_performance.get('win_rate', 0.5)
        profit_factor = recent_performance.get('profit_factor', 1.0)
        total_trades = recent_performance.get('total_trades', 0)
        
        # Determine if we should adjust based on performance
        if win_rate >= 0.65 and profit_factor >= 1.5:
            # High performance - can afford to be more selective
            return self._raise_threshold_for_performance(win_rate, profit_factor, total_trades)
        elif win_rate < 0.45 or profit_factor < 0.8:
            # Poor performance - be more selective or seek different signals
            return self._raise_threshold_for_poor_performance(win_rate, profit_factor, total_trades)
        elif win_rate >= 0.50 and win_rate < 0.55 and profit_factor < 1.1:
            # Marginal performance - try lowering threshold for more opportunities
            return self._lower_threshold_for_marginal_performance(win_rate, profit_factor, total_trades)
        
        return False
    
    def _raise_threshold_for_performance(self, win_rate, profit_factor, total_trades):
        """Raise threshold when performance is strong."""
        old_threshold = self.current_threshold
        new_threshold = min(self.max_threshold,
                           self.current_threshold + self.adjustment_step)
        
        if new_threshold > old_threshold:
            self.current_threshold = new_threshold
            
            reason = (f"Raised threshold due to strong performance: "
                     f"win_rate={win_rate:.2%}, profit_factor={profit_factor:.2f}, "
                     f"trades={total_trades}. Being more selective.")
            
            self._log_adjustment(old_threshold, new_threshold, reason,
                               recent_win_rate=win_rate,
                               recent_profit_factor=profit_factor,
                               total_trades_analyzed=total_trades)
            return True
        
        return False
    
    def _raise_threshold_for_poor_performance(self, win_rate, profit_factor, total_trades):
        """Raise threshold when performance is poor to be more selective."""
        old_threshold = self.current_threshold
        new_threshold = min(self.max_threshold,
                           self.current_threshold + self.adjustment_step * 1.5)
        
        if new_threshold > old_threshold:
            self.current_threshold = new_threshold
            
            reason = (f"Raised threshold due to poor performance: "
                     f"win_rate={win_rate:.2%}, profit_factor={profit_factor:.2f}, "
                     f"trades={total_trades}. Need higher quality signals.")
            
            self._log_adjustment(old_threshold, new_threshold, reason,
                               recent_win_rate=win_rate,
                               recent_profit_factor=profit_factor,
                               total_trades_analyzed=total_trades)
            return True
        
        return False
    
    def _lower_threshold_for_marginal_performance(self, win_rate, profit_factor, total_trades):
        """Lower threshold when performance is marginal to seek more opportunities."""
        old_threshold = self.current_threshold
        new_threshold = max(self.min_threshold,
                           self.current_threshold - self.adjustment_step)
        
        if new_threshold < old_threshold:
            self.current_threshold = new_threshold
            
            reason = (f"Lowered threshold due to marginal performance: "
                     f"win_rate={win_rate:.2%}, profit_factor={profit_factor:.2f}, "
                     f"trades={total_trades}. Seeking more opportunities.")
            
            self._log_adjustment(old_threshold, new_threshold, reason,
                               recent_win_rate=win_rate,
                               recent_profit_factor=profit_factor,
                               total_trades_analyzed=total_trades)
            return True
        
        return False
    
    def _log_adjustment(self, old_threshold, new_threshold, reason, 
                       cycles_without_signal=0, recent_win_rate=None, 
                       recent_profit_factor=None, total_trades_analyzed=0):
        """Log threshold adjustment to database and logger."""
        logging.info(f"🤖 ADAPTIVE THRESHOLD: {old_threshold:.3f} → {new_threshold:.3f}")
        logging.info(f"   Reason: {reason}")
        
        # Store in database if available
        if self.db:
            adjustment_data = {
                'old_threshold': old_threshold,
                'new_threshold': new_threshold,
                'adjustment_reason': reason,
                'cycles_without_signal': cycles_without_signal,
                'recent_win_rate': recent_win_rate,
                'recent_profit_factor': recent_profit_factor,
                'total_trades_analyzed': total_trades_analyzed
            }
            self.db.store_threshold_adjustment(adjustment_data)
    
    def get_current_threshold(self):
        """Get the current dynamic threshold value."""
        return self.current_threshold
    
    def reset_to_base(self):
        """Reset threshold to base value (useful for testing or manual intervention)."""
        old_threshold = self.current_threshold
        self.current_threshold = self.base_threshold
        self.cycles_without_signal = 0
        
        reason = "Manual reset to base threshold"
        self._log_adjustment(old_threshold, self.base_threshold, reason)
    
    def get_status(self):
        """Get current status of adaptive threshold manager."""
        return {
            'current_threshold': self.current_threshold,
            'base_threshold': self.base_threshold,
            'cycles_without_signal': self.cycles_without_signal,
            'min_threshold': self.min_threshold,
            'max_threshold': self.max_threshold,
            'adjustment_step': self.adjustment_step
        }
