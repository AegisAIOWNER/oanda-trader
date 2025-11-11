"""
Enhanced monitoring and logging system for trading bot.
Provides structured logging, health checks, and performance metrics.
"""
import logging
import json
from datetime import datetime, timedelta
from collections import deque, defaultdict
import time


class StructuredLogger:
    """
    Structured logging with different severity levels and context.
    """
    
    def __init__(self, name='TradingBot', log_level=logging.INFO):
        """
        Initialize structured logger.
        
        Args:
            name: Logger name
            log_level: Logging level
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)
        
        # Create console handler with formatting
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(log_level)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        self.context = {}  # Current context for logging
    
    def set_context(self, **kwargs):
        """Set context variables for subsequent log entries."""
        self.context.update(kwargs)
    
    def clear_context(self):
        """Clear all context variables."""
        self.context = {}
    
    def _format_message(self, message, **kwargs):
        """Format message with context."""
        all_context = {**self.context, **kwargs}
        if all_context:
            context_str = ' '.join([f"{k}={v}" for k, v in all_context.items()])
            return f"{message} | {context_str}"
        return message
    
    def debug(self, message, **kwargs):
        """Log debug message with context."""
        self.logger.debug(self._format_message(message, **kwargs))
    
    def info(self, message, **kwargs):
        """Log info message with context."""
        self.logger.info(self._format_message(message, **kwargs))
    
    def warning(self, message, **kwargs):
        """Log warning message with context."""
        self.logger.warning(self._format_message(message, **kwargs))
    
    def error(self, message, **kwargs):
        """Log error message with context."""
        self.logger.error(self._format_message(message, **kwargs))
    
    def critical(self, message, **kwargs):
        """Log critical message with context."""
        self.logger.critical(self._format_message(message, **kwargs))
    
    def log_trade_decision(self, instrument, signal, confidence, action, reason):
        """Log trade decision with structured information."""
        self.info(
            f"Trade Decision: {action}",
            instrument=instrument,
            signal=signal,
            confidence=f"{confidence:.3f}",
            reason=reason
        )
    
    def log_order_result(self, instrument, order_type, result, **details):
        """Log order execution result."""
        self.info(
            f"Order Result: {result}",
            instrument=instrument,
            order_type=order_type,
            **details
        )
    
    def log_risk_check(self, check_type, passed, reason, **details):
        """Log risk management check."""
        level = self.info if passed else self.warning
        level(
            f"Risk Check: {check_type} - {'PASSED' if passed else 'FAILED'}",
            reason=reason,
            **details
        )
    
    def log_api_error(self, endpoint, error, retry_count=0):
        """Log API error with details."""
        self.error(
            f"API Error: {endpoint}",
            error=str(error),
            retry_count=retry_count
        )
    
    def log_validation_error(self, validation_type, error_message, **details):
        """Log validation error."""
        self.warning(
            f"Validation Failed: {validation_type}",
            error=error_message,
            **details
        )


class PerformanceMonitor:
    """
    Monitors bot performance metrics and health indicators.
    """
    
    def __init__(self, window_size=100):
        """
        Initialize performance monitor.
        
        Args:
            window_size: Number of recent operations to track
        """
        self.window_size = window_size
        
        # API performance metrics
        self.api_call_times = deque(maxlen=window_size)
        self.api_errors = deque(maxlen=window_size)
        self.api_error_count = 0
        self.api_success_count = 0
        
        # Trading metrics
        self.trade_attempts = 0
        self.trade_successes = 0
        self.trade_failures = 0
        self.trades_rejected_by_risk = 0
        self.trades_rejected_by_validation = 0
        
        # Cycle metrics
        self.cycle_times = deque(maxlen=window_size)
        self.signals_found = deque(maxlen=window_size)
        
        # Error tracking
        self.error_types = defaultdict(int)
        
        # Health status
        self.last_successful_api_call = None
        self.last_successful_trade = None
        self.last_cycle_time = None
        
        self.start_time = datetime.now()
    
    def record_api_call(self, success, duration, error=None):
        """
        Record API call metrics.
        
        Args:
            success: Whether the call succeeded
            duration: Call duration in seconds
            error: Error message if failed
        """
        self.api_call_times.append(duration)
        
        if success:
            self.api_success_count += 1
            self.last_successful_api_call = datetime.now()
        else:
            self.api_error_count += 1
            self.api_errors.append({
                'time': datetime.now(),
                'error': str(error) if error else 'Unknown'
            })
            if error:
                error_type = type(error).__name__
                self.error_types[error_type] += 1
    
    def record_trade_attempt(self, success, rejection_reason=None):
        """
        Record trade attempt.
        
        Args:
            success: Whether the trade was placed
            rejection_reason: Reason if rejected (risk, validation, etc.)
        """
        self.trade_attempts += 1
        
        if success:
            self.trade_successes += 1
            self.last_successful_trade = datetime.now()
        else:
            self.trade_failures += 1
            if rejection_reason:
                if 'risk' in rejection_reason.lower():
                    self.trades_rejected_by_risk += 1
                elif 'validation' in rejection_reason.lower():
                    self.trades_rejected_by_validation += 1
    
    def record_cycle(self, duration, signals_found_count):
        """
        Record trading cycle metrics.
        
        Args:
            duration: Cycle duration in seconds
            signals_found_count: Number of signals found in cycle
        """
        self.cycle_times.append(duration)
        self.signals_found.append(signals_found_count)
        self.last_cycle_time = datetime.now()
    
    def get_api_metrics(self):
        """Get API performance metrics."""
        total_calls = self.api_success_count + self.api_error_count
        error_rate = (self.api_error_count / total_calls * 100) if total_calls > 0 else 0
        
        avg_duration = sum(self.api_call_times) / len(self.api_call_times) if self.api_call_times else 0
        
        return {
            'total_calls': total_calls,
            'success_count': self.api_success_count,
            'error_count': self.api_error_count,
            'error_rate_pct': error_rate,
            'avg_call_duration_ms': avg_duration * 1000,
            'recent_errors': list(self.api_errors)[-5:],  # Last 5 errors
            'last_successful_call': self.last_successful_api_call
        }
    
    def get_trade_metrics(self):
        """Get trading metrics."""
        success_rate = (self.trade_successes / self.trade_attempts * 100) if self.trade_attempts > 0 else 0
        
        return {
            'total_attempts': self.trade_attempts,
            'successes': self.trade_successes,
            'failures': self.trade_failures,
            'success_rate_pct': success_rate,
            'rejected_by_risk': self.trades_rejected_by_risk,
            'rejected_by_validation': self.trades_rejected_by_validation,
            'last_successful_trade': self.last_successful_trade
        }
    
    def get_cycle_metrics(self):
        """Get cycle performance metrics."""
        avg_cycle_time = sum(self.cycle_times) / len(self.cycle_times) if self.cycle_times else 0
        avg_signals = sum(self.signals_found) / len(self.signals_found) if self.signals_found else 0
        
        return {
            'total_cycles': len(self.cycle_times),
            'avg_cycle_time_sec': avg_cycle_time,
            'avg_signals_per_cycle': avg_signals,
            'last_cycle_time': self.last_cycle_time
        }
    
    def get_health_status(self):
        """
        Get overall health status of the bot.
        
        Returns:
            dict: Health status with indicators
        """
        now = datetime.now()
        uptime = (now - self.start_time).total_seconds()
        
        # Check API health
        api_healthy = True
        api_issue = None
        if self.last_successful_api_call:
            time_since_api = (now - self.last_successful_api_call).total_seconds()
            if time_since_api > 600:  # 10 minutes
                api_healthy = False
                api_issue = f"No successful API call in {time_since_api/60:.1f} minutes"
        
        # Check error rate
        total_calls = self.api_success_count + self.api_error_count
        error_rate = (self.api_error_count / total_calls) if total_calls > 0 else 0
        error_rate_healthy = error_rate < 0.2  # Less than 20% error rate
        
        # Overall status
        overall_healthy = api_healthy and error_rate_healthy
        status = 'HEALTHY' if overall_healthy else 'DEGRADED'
        
        return {
            'status': status,
            'uptime_seconds': uptime,
            'uptime_hours': uptime / 3600,
            'api_healthy': api_healthy,
            'api_issue': api_issue,
            'error_rate_healthy': error_rate_healthy,
            'error_rate': error_rate,
            'last_successful_api_call': self.last_successful_api_call,
            'last_successful_trade': self.last_successful_trade,
            'error_types': dict(self.error_types)
        }
    
    def get_summary(self):
        """Get complete performance summary."""
        return {
            'health': self.get_health_status(),
            'api_metrics': self.get_api_metrics(),
            'trade_metrics': self.get_trade_metrics(),
            'cycle_metrics': self.get_cycle_metrics()
        }
    
    def reset(self):
        """Reset all metrics (for testing or manual intervention)."""
        self.api_call_times.clear()
        self.api_errors.clear()
        self.api_error_count = 0
        self.api_success_count = 0
        self.trade_attempts = 0
        self.trade_successes = 0
        self.trade_failures = 0
        self.trades_rejected_by_risk = 0
        self.trades_rejected_by_validation = 0
        self.cycle_times.clear()
        self.signals_found.clear()
        self.error_types.clear()
        self.start_time = datetime.now()


class HealthChecker:
    """
    Performs health checks on bot components.
    """
    
    @staticmethod
    def check_api_connectivity(api, account_id):
        """
        Check API connectivity.
        
        Args:
            api: API client
            account_id: Account ID
            
        Returns:
            tuple: (is_healthy, message)
        """
        try:
            import oandapyV20.endpoints.accounts as accounts
            r = accounts.AccountSummary(accountID=account_id)
            response = api.request(r)
            
            if response and 'account' in response:
                return True, "API connectivity OK"
            else:
                return False, "API response missing account data"
        
        except Exception as e:
            return False, f"API connectivity failed: {str(e)}"
    
    @staticmethod
    def check_database_connectivity(db):
        """
        Check database connectivity.
        
        Args:
            db: Database instance
            
        Returns:
            tuple: (is_healthy, message)
        """
        try:
            # Try a simple query
            metrics = db.get_performance_metrics(days=1)
            return True, "Database connectivity OK"
        
        except Exception as e:
            return False, f"Database connectivity failed: {str(e)}"
    
    @staticmethod
    def check_balance_sufficient(balance, min_balance=100):
        """
        Check if account balance is sufficient.
        
        Args:
            balance: Current balance
            min_balance: Minimum required balance
            
        Returns:
            tuple: (is_healthy, message)
        """
        if balance >= min_balance:
            return True, f"Balance sufficient: {balance:.2f}"
        else:
            return False, f"Balance too low: {balance:.2f} < {min_balance:.2f}"
    
    @staticmethod
    def perform_full_health_check(api, account_id, db, balance, min_balance=100):
        """
        Perform complete health check.
        
        Args:
            api: API client
            account_id: Account ID
            db: Database instance
            balance: Current balance
            min_balance: Minimum balance threshold
            
        Returns:
            dict: Health check results
        """
        results = {}
        
        # Check API
        api_healthy, api_msg = HealthChecker.check_api_connectivity(api, account_id)
        results['api'] = {'healthy': api_healthy, 'message': api_msg}
        
        # Check database
        db_healthy, db_msg = HealthChecker.check_database_connectivity(db)
        results['database'] = {'healthy': db_healthy, 'message': db_msg}
        
        # Check balance
        balance_healthy, balance_msg = HealthChecker.check_balance_sufficient(balance, min_balance)
        results['balance'] = {'healthy': balance_healthy, 'message': balance_msg}
        
        # Overall status
        overall_healthy = api_healthy and db_healthy and balance_healthy
        results['overall'] = {
            'healthy': overall_healthy,
            'status': 'HEALTHY' if overall_healthy else 'UNHEALTHY'
        }
        
        return results
