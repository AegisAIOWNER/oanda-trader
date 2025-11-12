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
    1. Usable margin = available_margin × (1 - margin_buffer)  # Use (1-buffer)% of available margin
    2. Max margin from balance = balance × max_margin_usage    # Don't use > 50% of balance
    3. Max allowed margin = min(usable_margin, max_margin_from_balance)
    4. Max units = (max_allowed_margin × estimated_leverage) / current_price
    """
```

### Key Parameters

- **available_margin**: Retrieved from Oanda API via `get_margin_info()`
- **current_price**: Current market price of the instrument
- **margin_buffer**: Percentage of available margin to keep as safety buffer (default: 0.50 = 50%)
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
Margin Buffer: 50%

Calculation:
- Usable margin = $9,000 × (1 - 0.50) = $4,500
- Max from balance = $10,000 × 0.50 = $5,000
- Max allowed margin = min($4,500, $5,000) = $4,500
- Max units = ($4,500 × 20) / 1.1 = ~81,818 units

Result: 81,818 units (vs 200,000 with risk-based)
```

### Scenario 2: USD_SGD Trade (High Leverage)
```
Balance: $5,000
Available Margin: $4,500
Current Price: 1.3500
Stop Loss: 20 pips
Margin Buffer: 50%

Calculation:
- Usable margin = $4,500 × (1 - 0.50) = $2,250
- Max from balance = $5,000 × 0.50 = $2,500
- Max allowed margin = min($2,250, $2,500) = $2,250
- Max units = ($2,250 × 20) / 1.35 = ~33,333 units

Result: 33,333 units (prevents INSUFFICIENT_MARGIN)
```

### Scenario 3: Low Margin Scenario
```
Balance: $10,000
Available Margin: $500 (very low)
Current Price: 1.2000
Margin Buffer: 50%

Calculation:
- Usable margin = $500 × (1 - 0.50) = $250
- Max from balance = $10,000 × 0.50 = $5,000
- Max allowed margin = min($250, $5,000) = $250
- Max units = ($250 × 20) / 1.2 = ~4,166 units

Result: 4,166 units (better than old formula's 0/minimum)
Note: The new formula handles low margin scenarios better
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
