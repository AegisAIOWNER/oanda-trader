"""
Volatility Detector - Monitors market volatility across multiple instruments
and provides conditional strategy adjustments based on volatility state.
"""
import logging
from datetime import datetime
import numpy as np


class VolatilityDetector:
    """
    Detects market volatility across multiple instruments using ATR analysis.
    Provides conditional strategy adjustments for low volatility conditions.
    """
    
    def __init__(self, low_threshold=0.0005, normal_threshold=0.0015, 
                 adjustment_mode='adaptive', atr_window=10):
        """
        Initialize volatility detector.
        
        Args:
            low_threshold: ATR threshold below which volatility is considered low
            normal_threshold: ATR threshold above which volatility is considered normal/high
            adjustment_mode: How to adjust in low volatility ('aggressive_threshold', 
                           'widen_stops', 'skip_cycles', 'adaptive')
            atr_window: Number of recent ATR readings to average for volatility calculation
        """
        self.low_threshold = low_threshold
        self.normal_threshold = normal_threshold
        self.adjustment_mode = adjustment_mode
        self.atr_window = atr_window
        
        # Tracking state
        self.current_volatility_state = 'UNKNOWN'
        self.current_avg_atr = 0.0
        self.atr_history = []
        self.last_detection_time = None
        self.consecutive_low_volatility_cycles = 0
        
        logging.info(f"Volatility detector initialized: low_threshold={low_threshold:.6f}, "
                     f"normal_threshold={normal_threshold:.6f}, mode={adjustment_mode}")
    
    def detect_volatility(self, atr_readings):
        """
        Detect current market volatility state based on ATR readings from multiple instruments.
        
        Args:
            atr_readings: List of ATR values from different instruments
            
        Returns:
            dict: {
                'state': 'LOW' | 'NORMAL' | 'HIGH',
                'avg_atr': float,
                'confidence': float (0.0-1.0),
                'readings_count': int
            }
        """
        if not atr_readings:
            logging.warning("No ATR readings provided for volatility detection")
            return {
                'state': 'UNKNOWN',
                'avg_atr': 0.0,
                'confidence': 0.0,
                'readings_count': 0
            }
        
        # Filter out zero or invalid ATR values
        valid_atrs = [atr for atr in atr_readings if atr > 0]
        
        if not valid_atrs:
            logging.warning("No valid ATR readings found")
            return {
                'state': 'UNKNOWN',
                'avg_atr': 0.0,
                'confidence': 0.0,
                'readings_count': 0
            }
        
        # Calculate average ATR across all instruments
        avg_atr = np.mean(valid_atrs)
        
        # Add to history for trend analysis
        self.atr_history.append(avg_atr)
        if len(self.atr_history) > self.atr_window:
            self.atr_history.pop(0)
        
        # Determine volatility state
        if avg_atr < self.low_threshold:
            state = 'LOW'
            self.consecutive_low_volatility_cycles += 1
        elif avg_atr >= self.normal_threshold:
            state = 'HIGH'
            self.consecutive_low_volatility_cycles = 0
        else:
            state = 'NORMAL'
            self.consecutive_low_volatility_cycles = 0
        
        # Calculate confidence based on consistency of recent readings
        confidence = self._calculate_confidence(valid_atrs, state)
        
        # Update state
        self.current_volatility_state = state
        self.current_avg_atr = avg_atr
        self.last_detection_time = datetime.now()
        
        logging.info(f"📊 VOLATILITY DETECTION: State={state}, Avg ATR={avg_atr:.6f}, "
                     f"Confidence={confidence:.2f}, Readings={len(valid_atrs)}, "
                     f"Consecutive Low Cycles={self.consecutive_low_volatility_cycles}")
        
        return {
            'state': state,
            'avg_atr': avg_atr,
            'confidence': confidence,
            'readings_count': len(valid_atrs),
            'consecutive_low_cycles': self.consecutive_low_volatility_cycles
        }
    
    def _calculate_confidence(self, atr_readings, state):
        """
        Calculate confidence in volatility state detection based on consistency.
        
        Args:
            atr_readings: List of ATR values
            state: Detected volatility state
            
        Returns:
            float: Confidence score (0.0-1.0)
        """
        if len(atr_readings) < 2:
            return 0.5
        
        # Calculate coefficient of variation (std/mean)
        std = np.std(atr_readings)
        mean = np.mean(atr_readings)
        cv = std / mean if mean > 0 else 1.0
        
        # Lower CV means more consistent readings, higher confidence
        # CV typically ranges from 0.1 to 1.0 for ATR
        confidence = max(0.0, min(1.0, 1.0 - cv))
        
        # Boost confidence if we have historical consistency
        if len(self.atr_history) >= 3:
            recent_avg = np.mean(self.atr_history)
            if state == 'LOW' and recent_avg < self.low_threshold:
                confidence = min(1.0, confidence + 0.1)
            elif state == 'HIGH' and recent_avg >= self.normal_threshold:
                confidence = min(1.0, confidence + 0.1)
        
        return confidence
    
    def get_threshold_adjustment(self, current_threshold, base_adjustment_step):
        """
        Get adjusted threshold parameters for low volatility conditions.
        
        Args:
            current_threshold: Current confidence threshold
            base_adjustment_step: Base adjustment step size
            
        Returns:
            dict: {
                'adjusted_threshold': float,
                'adjusted_step': float,
                'reason': str
            }
        """
        if self.current_volatility_state != 'LOW':
            return {
                'adjusted_threshold': current_threshold,
                'adjusted_step': base_adjustment_step,
                'reason': f'Normal volatility mode (state={self.current_volatility_state})'
            }
        
        # In low volatility, be more aggressive with threshold lowering
        if self.adjustment_mode in ['aggressive_threshold', 'adaptive']:
            # Increase adjustment step by 2x-3x depending on how long we've been low
            multiplier = min(3.0, 1.5 + (self.consecutive_low_volatility_cycles * 0.3))
            adjusted_step = base_adjustment_step * multiplier
            
            # Also lower threshold more aggressively
            aggressive_reduction = base_adjustment_step * multiplier
            adjusted_threshold = max(0.4, current_threshold - aggressive_reduction)
            
            reason = (f"Low volatility detected (avg_atr={self.current_avg_atr:.6f}): "
                     f"increasing adjustment speed by {multiplier:.1f}x, "
                     f"lowering threshold more aggressively")
            
            logging.info(f"🔧 VOLATILITY ADJUSTMENT: {reason}")
            
            return {
                'adjusted_threshold': adjusted_threshold,
                'adjusted_step': adjusted_step,
                'reason': reason
            }
        
        return {
            'adjusted_threshold': current_threshold,
            'adjusted_step': base_adjustment_step,
            'reason': 'Low volatility but aggressive_threshold mode not enabled'
        }
    
    def get_stop_profit_adjustment(self, base_stop_multiplier, base_profit_multiplier):
        """
        Get adjusted stop-loss and take-profit multipliers for current volatility.
        
        Args:
            base_stop_multiplier: Base ATR stop loss multiplier
            base_profit_multiplier: Base ATR take profit multiplier
            
        Returns:
            dict: {
                'stop_multiplier': float,
                'profit_multiplier': float,
                'reason': str
            }
        """
        if self.current_volatility_state != 'LOW':
            return {
                'stop_multiplier': base_stop_multiplier,
                'profit_multiplier': base_profit_multiplier,
                'reason': f'Normal volatility - using base multipliers (state={self.current_volatility_state})'
            }
        
        # In low volatility, widen stops and targets to avoid whipsaws
        if self.adjustment_mode in ['widen_stops', 'adaptive']:
            # Widen both stop and profit by 1.5x-2x
            stop_adjustment = 1.5 + (self.consecutive_low_volatility_cycles * 0.1)
            profit_adjustment = 1.5 + (self.consecutive_low_volatility_cycles * 0.1)
            
            adjusted_stop = base_stop_multiplier * stop_adjustment
            adjusted_profit = base_profit_multiplier * profit_adjustment
            
            reason = (f"Low volatility detected (avg_atr={self.current_avg_atr:.6f}): "
                     f"widening stops to {adjusted_stop:.1f}x and profits to {adjusted_profit:.1f}x "
                     f"to avoid whipsaws")
            
            logging.info(f"🎯 STOP/PROFIT ADJUSTMENT: {reason}")
            
            return {
                'stop_multiplier': adjusted_stop,
                'profit_multiplier': adjusted_profit,
                'reason': reason
            }
        
        return {
            'stop_multiplier': base_stop_multiplier,
            'profit_multiplier': base_profit_multiplier,
            'reason': 'Low volatility but widen_stops mode not enabled'
        }
    
    def should_skip_cycle(self):
        """
        Determine if the trading cycle should be skipped due to low volatility.
        
        Returns:
            dict: {
                'skip': bool,
                'reason': str
            }
        """
        if self.adjustment_mode != 'skip_cycles':
            return {
                'skip': False,
                'reason': 'skip_cycles mode not enabled'
            }
        
        if self.current_volatility_state == 'LOW':
            # Skip if we've had multiple consecutive low volatility cycles
            if self.consecutive_low_volatility_cycles >= 3:
                reason = (f"Skipping cycle: {self.consecutive_low_volatility_cycles} consecutive "
                         f"low volatility cycles (avg_atr={self.current_avg_atr:.6f} < "
                         f"threshold={self.low_threshold:.6f})")
                
                logging.info(f"⏸️  CYCLE SKIP: {reason}")
                
                return {
                    'skip': True,
                    'reason': reason
                }
        
        return {
            'skip': False,
            'reason': f'Volatility state is {self.current_volatility_state}'
        }
    
    def get_status(self):
        """
        Get current status of volatility detector.
        
        Returns:
            dict: Current state and configuration
        """
        return {
            'state': self.current_volatility_state,
            'avg_atr': self.current_avg_atr,
            'low_threshold': self.low_threshold,
            'normal_threshold': self.normal_threshold,
            'adjustment_mode': self.adjustment_mode,
            'consecutive_low_cycles': self.consecutive_low_volatility_cycles,
            'atr_history_length': len(self.atr_history),
            'last_detection': self.last_detection_time.isoformat() if self.last_detection_time else None
        }
    
    def reset(self):
        """Reset volatility detector state (useful for testing or manual intervention)."""
        self.current_volatility_state = 'UNKNOWN'
        self.current_avg_atr = 0.0
        self.atr_history = []
        self.consecutive_low_volatility_cycles = 0
        logging.info("Volatility detector state reset")
