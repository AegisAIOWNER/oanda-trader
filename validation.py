"""
Input validation and data integrity checks for trading bot.
Ensures all data entering the system is validated to prevent errors.
"""
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import pytz


class DataValidator:
    """Validates trading data and inputs to prevent errors."""
    
    @staticmethod
    def validate_candle_data(df, instrument, min_candles=5):
        """
        Validate candle data completeness and integrity.
        
        Args:
            df: DataFrame with candle data (must have: time, open, high, low, close, volume)
            instrument: Instrument name for logging
            min_candles: Minimum number of candles required
            
        Returns:
            tuple: (is_valid, error_message)
        """
        if df is None or df.empty:
            return False, f"No candle data received for {instrument}"
        
        # Adjust minimum candles for instruments with limited historical data
        effective_min = 1 if '10Y' in instrument else min_candles
        
        # Check minimum candles
        if len(df) < effective_min:
            return False, f"Insufficient candles for {instrument}: {len(df)} < {effective_min}"
        
        # Check required columns
        required_columns = ['time', 'open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return False, f"Missing required columns for {instrument}: {missing_columns}"
        
        # Check for NaN values in critical columns
        critical_columns = ['open', 'high', 'low', 'close']
        for col in critical_columns:
            nan_count = df[col].isna().sum()
            if nan_count > 0:
                return False, f"Found {nan_count} NaN values in {col} for {instrument}"
        
        # Validate OHLC relationship (high >= low, high >= open, high >= close, low <= open, low <= close)
        invalid_rows = df[
            (df['high'] < df['low']) |
            (df['high'] < df['open']) |
            (df['high'] < df['close']) |
            (df['low'] > df['open']) |
            (df['low'] > df['close'])
        ]
        if len(invalid_rows) > 0:
            return False, f"Invalid OHLC relationships in {len(invalid_rows)} candles for {instrument}"
        
        # Check for zero or negative prices
        price_columns = ['open', 'high', 'low', 'close']
        for col in price_columns:
            if (df[col] <= 0).any():
                return False, f"Found zero or negative prices in {col} for {instrument}"
        
        # Check for duplicate timestamps
        if df['time'].duplicated().any():
            dup_count = df['time'].duplicated().sum()
            logging.warning(f"Found {dup_count} duplicate timestamps for {instrument}")
        
        # Check for excessive gaps in data (candles more than 2x expected apart)
        if len(df) > 1:
            # This is a heuristic - could be improved with granularity info
            pass  # Skip for now as we don't have granularity in this context
        
        return True, "Valid candle data"
    
    @staticmethod
    def validate_atr(atr_value, instrument, max_atr_multiplier=100):
        """
        Validate ATR calculation results.
        
        Args:
            atr_value: Calculated ATR value
            instrument: Instrument name for logging
            max_atr_multiplier: Maximum reasonable ATR as multiplier of pip size
            
        Returns:
            tuple: (is_valid, error_message, sanitized_atr)
        """
        if atr_value is None:
            return False, f"ATR is None for {instrument}", 0.0
        
        if pd.isna(atr_value):
            return False, f"ATR is NaN for {instrument}", 0.0
        
        if not isinstance(atr_value, (int, float, np.integer, np.floating)):
            return False, f"ATR has invalid type {type(atr_value)} for {instrument}", 0.0
        
        if atr_value < 0:
            return False, f"ATR is negative ({atr_value}) for {instrument}", 0.0
        
        if atr_value == 0:
            logging.warning(f"ATR is zero for {instrument}, using fallback")
            return True, "ATR is zero, fallback needed", 0.0
        
        # Check for unreasonably large ATR values
        # This would catch data errors or extreme volatility
        pip_size = 0.01 if 'JPY' in instrument else 0.0001
        if atr_value > pip_size * max_atr_multiplier:
            logging.warning(f"ATR unusually large for {instrument}: {atr_value} (>{max_atr_multiplier} pips)")
            # Don't reject, but log it
        
        return True, "Valid ATR", float(atr_value)
    
    @staticmethod
    def validate_order_params(instrument, units, stop_loss_pips=None, take_profit_pips=None,
                             max_units=1000000, min_units=1):
        """
        Validate order parameters before submission.
        
        Args:
            instrument: Trading instrument
            units: Number of units to trade (positive)
            stop_loss_pips: Stop loss distance in pips
            take_profit_pips: Take profit distance in pips
            max_units: Maximum allowed units per order
            min_units: Minimum allowed units per order
            
        Returns:
            tuple: (is_valid, error_message)
        """
        if not instrument or not isinstance(instrument, str):
            return False, "Invalid instrument"
        
        # Validate units
        if units is None or not isinstance(units, (int, float, np.integer, np.floating)):
            return False, f"Invalid units type: {type(units)}"
        
        units = abs(float(units))  # Ensure positive
        
        if units < min_units:
            return False, f"Units {units} below minimum {min_units}"
        
        if units > max_units:
            return False, f"Units {units} exceeds maximum {max_units}"
        
        if not np.isfinite(units):
            return False, f"Units is not finite: {units}"
        
        # Validate stop loss
        if stop_loss_pips is not None:
            if not isinstance(stop_loss_pips, (int, float, np.integer, np.floating)):
                return False, f"Invalid stop loss type: {type(stop_loss_pips)}"
            
            if stop_loss_pips <= 0:
                return False, f"Stop loss must be positive: {stop_loss_pips}"
            
            if not np.isfinite(stop_loss_pips):
                return False, f"Stop loss is not finite: {stop_loss_pips}"
            
            # Reasonable range check (0.1 to 1000 pips)
            if stop_loss_pips < 0.1 or stop_loss_pips > 1000:
                return False, f"Stop loss out of reasonable range: {stop_loss_pips}"
        
        # Validate take profit
        if take_profit_pips is not None:
            if not isinstance(take_profit_pips, (int, float, np.integer, np.floating)):
                return False, f"Invalid take profit type: {type(take_profit_pips)}"
            
            if take_profit_pips <= 0:
                return False, f"Take profit must be positive: {take_profit_pips}"
            
            if not np.isfinite(take_profit_pips):
                return False, f"Take profit is not finite: {take_profit_pips}"
            
            # Reasonable range check (0.1 to 1000 pips)
            if take_profit_pips < 0.1 or take_profit_pips > 1000:
                return False, f"Take profit out of reasonable range: {take_profit_pips}"
        
        return True, "Valid order parameters"
    
    @staticmethod
    def is_market_closed(check_weekend=True, check_time=True):
        """
        Check if market is likely closed (weekends and major holidays).
        
        Args:
            check_weekend: Check for weekend hours
            check_time: Check for daily market close (Friday 5pm to Sunday 5pm EST)
            
        Returns:
            tuple: (is_closed, reason)
        """
        now_utc = datetime.now(pytz.UTC)
        
        # Convert to EST/EDT for market hours
        eastern = pytz.timezone('US/Eastern')
        now_est = now_utc.astimezone(eastern)
        
        if check_weekend:
            # Forex market closes Friday 5pm EST and opens Sunday 5pm EST
            weekday = now_est.weekday()  # Monday=0, Sunday=6
            hour = now_est.hour
            
            # Friday after 5pm
            if weekday == 4 and hour >= 17:
                return True, "Market closed: Friday after 5pm EST"
            
            # Saturday (all day)
            if weekday == 5:
                return True, "Market closed: Saturday"
            
            # Sunday before 5pm
            if weekday == 6 and hour < 17:
                return True, "Market closed: Sunday before 5pm EST"
        
        return False, "Market is open"
    
    @staticmethod
    def detect_price_gap(current_price, previous_price, threshold_pct=2.0):
        """
        Detect significant price gaps that might indicate data issues or extreme events.
        
        Args:
            current_price: Current price
            previous_price: Previous price
            threshold_pct: Gap threshold as percentage
            
        Returns:
            tuple: (has_gap, gap_percentage)
        """
        if current_price is None or previous_price is None:
            return False, 0.0
        
        if previous_price == 0:
            return False, 0.0
        
        gap_pct = abs((current_price - previous_price) / previous_price) * 100
        
        if gap_pct > threshold_pct:
            return True, gap_pct
        
        return False, gap_pct
    
    @staticmethod
    def validate_api_response(response, expected_keys=None):
        """
        Validate API response structure and content.
        
        Args:
            response: API response dictionary
            expected_keys: List of expected keys in response
            
        Returns:
            tuple: (is_valid, error_message)
        """
        if response is None:
            return False, "Response is None"
        
        if not isinstance(response, dict):
            return False, f"Response is not a dictionary: {type(response)}"
        
        # Check for error responses
        if 'errorMessage' in response:
            return False, f"API returned error: {response['errorMessage']}"
        
        if 'error' in response:
            return False, f"API returned error: {response.get('error', 'Unknown error')}"
        
        # Check expected keys if provided
        if expected_keys:
            missing_keys = [key for key in expected_keys if key not in response]
            if missing_keys:
                return False, f"Missing expected keys in response: {missing_keys}"
        
        return True, "Valid API response"


class RiskValidator:
    """Validates risk management parameters and constraints."""
    
    def __init__(self, max_open_positions=3, max_risk_per_trade=0.05, 
                 max_total_risk=0.15, max_slippage_pips=2.0):
        """
        Initialize risk validator with constraints.
        
        Args:
            max_open_positions: Maximum number of concurrent open positions
            max_risk_per_trade: Maximum risk percentage per trade (e.g., 0.05 = 5%)
            max_total_risk: Maximum total risk across all positions (e.g., 0.15 = 15%)
            max_slippage_pips: Maximum acceptable slippage in pips
        """
        self.max_open_positions = max_open_positions
        self.max_risk_per_trade = max_risk_per_trade
        self.max_total_risk = max_total_risk
        self.max_slippage_pips = max_slippage_pips
    
    def can_open_new_position(self, current_positions):
        """
        Check if a new position can be opened.
        
        Args:
            current_positions: Number of currently open positions
            
        Returns:
            tuple: (can_open, reason)
        """
        if current_positions >= self.max_open_positions:
            return False, f"Maximum open positions reached: {current_positions}/{self.max_open_positions}"
        
        return True, "OK to open new position"
    
    def validate_position_risk(self, risk_amount, balance):
        """
        Validate that position risk is within acceptable limits.
        
        Args:
            risk_amount: Risk amount in account currency
            balance: Account balance
            
        Returns:
            tuple: (is_valid, error_message)
        """
        if balance <= 0:
            return False, "Invalid balance"
        
        risk_pct = risk_amount / balance
        
        if risk_pct > self.max_risk_per_trade:
            return False, f"Risk per trade ({risk_pct*100:.2f}%) exceeds maximum ({self.max_risk_per_trade*100:.2f}%)"
        
        return True, "Risk within acceptable limits"
    
    def validate_total_exposure(self, new_risk, existing_risk, balance):
        """
        Validate that total risk exposure is within limits.
        
        Args:
            new_risk: Risk from new position
            existing_risk: Combined risk from existing positions
            balance: Account balance
            
        Returns:
            tuple: (is_valid, error_message)
        """
        if balance <= 0:
            return False, "Invalid balance"
        
        total_risk_pct = (new_risk + existing_risk) / balance
        
        if total_risk_pct > self.max_total_risk:
            return False, f"Total risk exposure ({total_risk_pct*100:.2f}%) exceeds maximum ({self.max_total_risk*100:.2f}%)"
        
        return True, "Total exposure within limits"
    
    def validate_slippage(self, expected_price, fill_price, instrument):
        """
        Validate that slippage is within acceptable limits.
        
        Args:
            expected_price: Expected fill price
            fill_price: Actual fill price
            instrument: Trading instrument
            
        Returns:
            tuple: (is_acceptable, slippage_pips, reason)
        """
        if expected_price is None or fill_price is None:
            return True, 0.0, "Unable to calculate slippage"
        
        if expected_price == 0:
            return True, 0.0, "Unable to calculate slippage"
        
        # Calculate pip size
        pip_size = 0.01 if 'JPY' in instrument else 0.0001
        
        # Calculate slippage in pips
        slippage_price = abs(fill_price - expected_price)
        slippage_pips = slippage_price / pip_size
        
        if slippage_pips > self.max_slippage_pips:
            return False, slippage_pips, f"Slippage ({slippage_pips:.2f} pips) exceeds maximum ({self.max_slippage_pips} pips)"
        
        return True, slippage_pips, "Acceptable slippage"