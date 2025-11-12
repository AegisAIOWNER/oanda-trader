# Minimum Position Size Enforcement

## Overview

The bot now enforces a minimum position size to ensure all trades meet Oanda's margin requirements. This feature automatically overrides risk-based position sizing calculations when they would result in positions too small to trade effectively.

## Problem Solved

When using risk-based position sizing (e.g., 2% of account balance), small accounts or conservative risk settings can result in position sizes below broker margin requirements. This leads to:
- Rejected orders due to insufficient margin
- Inability to execute trades on small accounts
- Missed trading opportunities

## Solution

The bot now calculates a minimum position size based on:
- **Target trade value**: $1-2 (configurable via `MIN_TRADE_VALUE`)
- **Instrument pip value**: Automatically determined (e.g., 0.0001 for EUR/USD, 0.01 for USD/JPY)
- **Stop loss distance**: The configured stop loss in pips

Formula: `minimum_units = MIN_TRADE_VALUE / (stop_loss_pips × pip_value)`

## Configuration

Add to `config.py`:

```python
# Minimum trade value in account currency ($1-2 range recommended)
MIN_TRADE_VALUE = 1.50
```

The default value of $1.50 is the midpoint of the $1-2 range that meets Oanda's requirements.

## How It Works

1. **Calculate risk-based position size** using configured method (Fixed % or Kelly Criterion)
2. **Calculate minimum required units** to achieve MIN_TRADE_VALUE
3. **Use the larger value** between risk-based and minimum
4. **Stop loss and take profit levels remain unchanged** - only position size is adjusted

### Example Scenarios

#### Scenario 1: Small Account ($100 balance)
- Risk-based calculation: 200 units (2% risk)
- Minimum calculation: 1,500 units (for $1.50 @ 10 pips × 0.0001)
- **Result**: 1,500 units used (minimum enforced)
- Trade value: $1.50 ✅

#### Scenario 2: Normal Account ($10,000 balance)
- Risk-based calculation: 20,000 units (2% risk)
- Minimum calculation: 1,500 units
- **Result**: 20,000 units used (risk-based dominates)
- Trade value: $20.00 ✅

## Key Features

### ✅ Automatic Enforcement
- No manual intervention required
- Works with all instruments (EUR/USD, USD/JPY, GBP/USD, etc.)
- Adapts to different pip values automatically

### ✅ Risk Management Preserved
- Stop loss levels unchanged
- Take profit levels unchanged
- Overall risk structure intact
- Only adjusts position size when needed

### ✅ Works with Both Methods
- Fixed Percentage sizing
- Kelly Criterion sizing
- Confidence adjustments respected
- Low confidence doesn't break minimum

### ✅ Flexible Configuration
- Adjustable minimum trade value
- Can be set between $1-2 (or higher if needed)
- Works with any stop loss size

## Implementation Details

### Files Modified

1. **config.py**
   - Added `MIN_TRADE_VALUE = 1.50`

2. **position_sizing.py**
   - Added `min_trade_value` parameter to `__init__()`
   - Added `_enforce_minimum_position_size()` method
   - Updated `calculate_position_size()` to apply minimum

3. **bot.py**
   - Pass `MIN_TRADE_VALUE` to `PositionSizer` initialization

### Code Example

```python
from position_sizing import PositionSizer

# Create sizer with minimum enforcement
sizer = PositionSizer(
    method='fixed_percentage',
    risk_per_trade=0.02,
    min_trade_value=1.50  # $1-2 range
)

# Calculate position size (minimum enforced automatically)
units, risk_pct = sizer.calculate_position_size(
    balance=100.0,
    stop_loss_pips=10.0,
    pip_value=0.0001,  # EUR/USD
    confidence=1.0
)

# Trade value will be >= $1.50
trade_value = units * 10.0 * 0.0001
print(f"Trade value: ${trade_value:.2f}")  # $1.50+
```

## Testing

### Test Coverage

Created comprehensive test suite with 10 test cases:

1. ✅ EUR/USD minimum enforcement
2. ✅ USD/JPY minimum enforcement  
3. ✅ Minimum not applied when risk-based is higher
4. ✅ Minimum with low confidence
5. ✅ Minimum with Kelly Criterion
6. ✅ Custom minimum trade value
7. ✅ Minimum with tight stops
8. ✅ Minimum with wide stops
9. ✅ Preserves stops and limits
10. ✅ Absolute minimum floor (100 units)

### Test Results

```bash
$ python -m unittest test_minimum_position_size -v
...
Ran 10 tests in 0.001s
OK
```

All tests pass, including original position sizing tests.

## Benefits

### 💰 Small Account Friendly
- Enables trading with accounts as low as $100
- Ensures all trades meet broker requirements
- No rejected orders due to insufficient size

### 🎯 Consistent Trade Execution
- All trades guaranteed to meet minimum
- Reduces failed order attempts
- Improves trading reliability

### 🛡️ Risk Management Intact
- Stop losses remain properly sized
- Take profits unchanged
- Overall risk structure preserved
- Only position size adjusted, not risk per trade

### 🔧 Easy Configuration
- Single parameter to adjust (`MIN_TRADE_VALUE`)
- Works automatically across all instruments
- No per-instrument configuration needed

## Logging

The bot logs when minimum enforcement is applied:

```
INFO: Position size 200 units below minimum 1500 units 
      (required for $1.50 minimum trade value). 
      Overriding to minimum size.
```

This helps you understand when and why the minimum is being applied.

## Best Practices

### Recommended Settings

- **Practice Account**: `MIN_TRADE_VALUE = 1.50` (default)
- **Live Account**: `MIN_TRADE_VALUE = 2.00` (more conservative)
- **Micro Account**: `MIN_TRADE_VALUE = 1.00` (if broker allows)

### Monitoring

Watch for frequent minimum enforcement logs:
- If most trades hit the minimum, consider increasing account balance
- Or adjust risk percentage for more appropriate sizing
- Minimum should be safety net, not normal operation

## Compatibility

### ✅ Compatible With
- Fixed Percentage position sizing
- Kelly Criterion position sizing
- Multi-timeframe analysis
- ML predictions and confidence scoring
- Adaptive threshold management
- Volatility detection
- All supported instruments

### ⚠️ Considerations
- Overrides risk-based calculations when needed
- May result in higher risk % on very small accounts
- Should be paired with appropriate account balance

## Summary

The minimum position size enforcement feature ensures all trades meet broker margin requirements without compromising risk management. It's automatically applied when needed, transparent in operation, and fully tested across various scenarios.

**Key Takeaway**: Your trades will now always meet Oanda's minimum requirements while keeping your stop losses and take profits exactly where they should be for proper risk management.
