"""
Error recovery module with exponential backoff for API failures.
"""
import time
import logging
from functools import wraps

class ExponentialBackoff:
    """Implement exponential backoff with configurable parameters."""
    
    def __init__(self, base_delay=1.0, max_delay=60.0, max_retries=5, exponential_base=2):
        """
        Initialize exponential backoff.
        
        Args:
            base_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            max_retries: Maximum number of retry attempts
            exponential_base: Base for exponential calculation (typically 2)
        """
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
        self.exponential_base = exponential_base
    
    def calculate_delay(self, attempt):
        """
        Calculate delay for a given attempt.
        
        Args:
            attempt: Current attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        delay = self.base_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)
    
    def execute_with_retry(self, func, *args, **kwargs):
        """
        Execute a function with exponential backoff retry logic.
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Function result if successful
            
        Raises:
            Last exception if all retries fail
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                result = func(*args, **kwargs)
                if attempt > 0:
                    logging.info(f"Function succeeded on attempt {attempt + 1}")
                return result
                
            except Exception as e:
                last_exception = e
                
                # Check if we should retry
                if attempt < self.max_retries - 1:
                    delay = self.calculate_delay(attempt)
                    logging.warning(
                        f"Attempt {attempt + 1} failed: {str(e)}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    time.sleep(delay)
                else:
                    logging.error(
                        f"All {self.max_retries} attempts failed. "
                        f"Last error: {str(e)}"
                    )
        
        # If we get here, all retries failed
        raise last_exception

def with_exponential_backoff(base_delay=1.0, max_delay=60.0, max_retries=5, exponential_base=2):
    """
    Decorator for adding exponential backoff to a function.
    
    Args:
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        max_retries: Maximum number of retry attempts
        exponential_base: Base for exponential calculation
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            backoff = ExponentialBackoff(
                base_delay=base_delay,
                max_delay=max_delay,
                max_retries=max_retries,
                exponential_base=exponential_base
            )
            return backoff.execute_with_retry(func, *args, **kwargs)
        return wrapper
    return decorator

class CircuitBreaker:
    """
    Circuit breaker pattern for preventing cascading failures.
    Opens circuit after threshold failures, closes after successful operations.
    """
    
    def __init__(self, failure_threshold=5, timeout=60):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before attempting to close circuit
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'  # 'closed', 'open', 'half_open'
    
    def call(self, func, *args, **kwargs):
        """
        Call a function through the circuit breaker.
        
        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result if successful
            
        Raises:
            Exception if circuit is open or function fails
        """
        if self.state == 'open':
            # Check if timeout has passed
            if time.time() - self.last_failure_time > self.timeout:
                self.state = 'half_open'
                logging.info("Circuit breaker entering half-open state")
            else:
                raise Exception(
                    f"Circuit breaker is open. "
                    f"Too many failures ({self.failure_count}). "
                    f"Try again later."
                )
        
        try:
            result = func(*args, **kwargs)
            
            # Success - reset or close circuit
            if self.state == 'half_open':
                self.state = 'closed'
                logging.info("Circuit breaker closed after successful call")
            
            self.failure_count = 0
            return result
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = 'open'
                logging.error(
                    f"Circuit breaker opened after {self.failure_count} failures"
                )
            
            raise e

# Global circuit breaker instance for API calls
api_circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)
