import time
import logging
from functools import wraps

class ExponentialBackoff:
    """Exponential backoff for retrying failed API calls."""
    
    def __init__(self, base_delay=1.0, max_delay=60.0, max_retries=5, backoff_factor=2.0):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
    
    def execute_with_retry(self, func):
        """Execute a function with exponential backoff retry."""
        last_exception = None
        delay = self.base_delay
        
        for attempt in range(self.max_retries):
            try:
                return func()
            except Exception as e:
                last_exception = e
                if attempt == self.max_retries - 1:
                    break
                
                logging.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.1f}s...")
                time.sleep(delay)
                delay = min(delay * self.backoff_factor, self.max_delay)
        
        logging.error(f"All {self.max_retries} attempts failed. Last error: {last_exception}")
        raise last_exception

class CircuitBreaker:
    """Circuit breaker pattern to prevent cascading failures."""
    
    def __init__(self, failure_threshold=5, recovery_timeout=60.0, expected_exception=Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = 'HALF_OPEN'
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            if self.state == 'HALF_OPEN':
                self.state = 'CLOSED'
                self.failure_count = 0
            return result
        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'
                logging.warning("Circuit breaker OPENED due to repeated failures")
            raise e

# Global circuit breaker instance
api_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)