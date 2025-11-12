# Margin-Based Position Sizing

## Overview

This document describes the margin-based position sizing feature implemented to prevent INSUFFICIENT_MARGIN errors for leveraged instruments like USD_SGD.

## Problem Statement

The previous position sizing logic calculated trade units based on risk percentage (e.g., 2% of account balance). For leveraged instruments, this approach could result in:
- Position sizes that exceed available margin
- INSUFFICIENT_MARGIN errors when placing orders
- Rejected trades despite having sufficient account balance

## Solution

Modified the position sizing logic to calculate units based on **available margin** rather than risk percentage, while still respecting the MARGIN_BUFFER configuration (50% of balance kept available).

## How It Works

### Margin-Based Calculation

```python
def calculate_margin_based(balance, available_margin, current_price, 
                          margin_buffer=0.50, max_margin_usage=0.50):
    """
    Calculate position size based on available margin.
    
    Formula:
    1. Max allowed margin = min(
          available_margin - (balance × margin_buffer),  # Leave 50% buffer
          balance × max_margin_usage                     # Don't use > 50% of balance
       )
    2. Max units = (max_allowed_margin × estimated_leverage) / current_price
    """
```

### Key Parameters

- **available_margin**: Retrieved from Oanda API via `get_margin_info()`
- **current_price**: Current market price of the instrument
- **margin_buffer**: Minimum margin to keep available (default: 0.50 = 50%)
- **max_margin_usage**: Maximum percentage of balance to use as margin (default: 0.50 = 50%)
- **estimated_leverage**: Conservative estimate of 20:1 (safer than typical 50:1)

## Integration with Bot

### Before (Risk-Based)
```python
# Old approach - risk percentage only
units, risk_pct = position_sizer.calculate_position_size(
    balance=current_balance,
    stop_loss_pips=sl,
    pip_value=pip_value,
    confidence=confidence
)
```

### After (Margin-Based)
```python
# New approach - margin-aware
margin_info = self.get_margin_info()
units, risk_pct = position_sizer.calculate_position_size(
    balance=current_balance,
    stop_loss_pips=sl,
    pip_value=pip_value,
    confidence=confidence,
    available_margin=margin_info['margin_available'],
    current_price=current_price,
    margin_buffer=MARGIN_BUFFER
)
```

## Benefits

1. **Prevents INSUFFICIENT_MARGIN Errors**: Calculates units that fit within available margin
2. **Leveraged Instrument Support**: Works correctly with high-leverage instruments like USD_SGD
3. **Respects Margin Buffer**: Maintains 50% margin buffer as per configuration
4. **Conservative Approach**: Uses 20:1 leverage estimate for safety
5. **Backward Compatible**: Falls back to risk-based sizing if margin info not provided
6. **Maintains Minimum Position Size**: Still enforces minimum trade value requirements

## Example Scenarios

### Scenario 1: EUR_USD Trade
```
Balance: $10,000
Available Margin: $9,000
Current Price: 1.1000
Stop Loss: 10 pips

Calculation:
- Max allowed margin = min(9000 - 5000, 5000) = $4,000
- Max units = (4000 × 20) / 1.1 = ~72,727 units

Result: 72,727 units (vs 200,000 with risk-based)
```

### Scenario 2: USD_SGD Trade (High Leverage)
```
Balance: $5,000
Available Margin: $4,500
Current Price: 1.3500
Stop Loss: 20 pips

Calculation:
- Max allowed margin = min(4500 - 2500, 2500) = $2,000
- Max units = (2000 × 20) / 1.35 = ~29,630 units

Result: 29,630 units (prevents INSUFFICIENT_MARGIN)
```

### Scenario 3: Low Margin Scenario
```
Balance: $10,000
Available Margin: $500 (very low)
Current Price: 1.2000

Calculation:
- Max allowed margin = min(500 - 5000, 5000) = 0 (negative)
- Falls back to minimum: 100 units

Result: 100 units (minimum enforced)
```

## Testing

### Unit Tests
- `test_margin_based_sizing.py`: 9 test cases covering various scenarios
- `test_margin_integration.py`: 4 integration test cases
- All existing tests pass (backward compatibility)

### Test Coverage
- ✅ EUR_USD standard pair
- ✅ USD_JPY with different pip value
- ✅ High leverage instruments (USD_SGD)
- ✅ Low margin scenarios
- ✅ Margin buffer enforcement
- ✅ Fallback to risk-based sizing
- ✅ Confidence adjustments
- ✅ Minimum position size enforcement

## Configuration

The following configuration values control margin-based sizing:

```python
# config.py
MARGIN_BUFFER = 0.50  # Keep 50% margin available
MIN_TRADE_VALUE = 1.50  # Minimum trade value ($1-2 range)
```

## API Integration

### New Method: `get_margin_info()`
```python
def get_margin_info(self):
    """Get margin information from account."""
    r = accounts.AccountSummary(accountID=self.account_id)
    response = self._rate_limited_request(r)
    return {
        'balance': float(response['account']['balance']),
        'margin_available': float(response['account']['marginAvailable']),
        'margin_used': float(response['account'].get('marginUsed', 0))
    }
```

## Fallback Behavior

If margin information is not provided to `calculate_position_size()`, the system automatically falls back to the original risk-based calculation methods:
- Fixed percentage method
- Kelly Criterion method (if enabled)

This ensures backward compatibility and allows both approaches to coexist.

## Future Enhancements

Potential improvements for future versions:
1. Dynamic leverage detection per instrument from API
2. Real-time margin monitoring and adjustment
3. Margin usage analytics and reporting
4. Position sizing optimization based on historical margin patterns

## Conclusion

Margin-based position sizing provides a robust solution for trading leveraged instruments while maintaining risk controls and preventing margin-related order rejections. The implementation is backward compatible, well-tested, and integrates seamlessly with the existing trading bot infrastructure.
