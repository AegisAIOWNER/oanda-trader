# Single-Trade Strategy Implementation

## Overview

This document describes the focused single-trade strategy implementation for the OANDA trading bot. The strategy prioritizes tracking one open position exclusively while maintaining a persistent list of qualified trading pairs.

## Key Features

### 1. Single Open Position (MAX_OPEN_POSITIONS = 1)

The bot now focuses on a single trade at a time, allowing for:
- More focused risk management
- Deeper position monitoring
- Better capital utilization per trade

**Configuration:**
```python
MAX_OPEN_POSITIONS = 1  # Only one position at a time
```

### 2. Enhanced Margin Utilization

While maintaining safety, the bot now uses more available balance:
- Keeps at least 50% margin available (increased from 5%)
- Allows for larger position sizes on high-confidence signals
- Better balance between risk and opportunity

**Configuration:**
```python
MARGIN_BUFFER = 0.50  # Keep 50% margin available
```

### 3. Confidence-Based Stop Loss Adjustment

For high-confidence signals (>0.8) indicating upward trends (BUY signals), the stop loss is automatically loosened:
- Standard SL multiplier: 0.5x ATR
- High confidence SL multiplier: 0.75x ATR (1.5x the standard)
- Only applies to BUY signals with confidence >= 0.8

**Configuration:**
```python
HIGH_CONFIDENCE_THRESHOLD = 0.8  # Threshold for high confidence
HIGH_CONFIDENCE_SL_MULTIPLIER = 1.5  # SL loosening factor
```

**Example:**
```
Normal signal: SL = 0.5 * ATR = 5 pips
High confidence BUY signal (0.85): SL = 0.5 * 1.5 * ATR = 7.5 pips
```

### 4. Exclusive Position Tracking

When a position is open:
- Bot skips scanning for new signals
- Focuses exclusively on monitoring the open trade
- Position monitoring thread handles TP/SL updates
- Trailing stops automatically adjust as profit grows

**Behavior:**
```
Cycle 1: No open position → Scan for signals → Open trade
Cycle 2: Position open → Skip signal scanning → Monitor position
Cycle 3: Position open → Skip signal scanning → Monitor position
Cycle 4: Position closed → Resume scanning for signals
```

### 5. Persistent Pair List Management

Instead of scanning random pairs each cycle, the bot maintains a persistent list:
- Pairs are stored across bot restarts (in `data/persistent_pairs.json`)
- Periodic requalification checks (every 5 minutes by default)
- Automatic removal of pairs that no longer qualify
- Dynamic addition of new qualifying pairs

**Configuration:**
```python
ENABLE_PERSISTENT_PAIRS = True
PERSISTENT_PAIRS_FILE = 'data/persistent_pairs.json'
PAIR_REQUALIFICATION_INTERVAL = 300  # 5 minutes
```

**Qualification Criteria:**
A pair is qualified if it:
1. Has sufficient historical data (>= 30 candles)
2. Has valid price data (no NaN, no zero/negative prices)
3. Has trading activity (volume > 0)

**Disqualification:**
A pair is automatically disqualified if:
- Insufficient data is available
- Price data is invalid
- No trading volume detected
- API errors occur repeatedly

## Architecture

### PersistentPairsManager

New class that handles pair lifecycle:

```python
class PersistentPairsManager:
    def __init__(self, storage_file, requalification_interval, max_pairs):
        """Initialize with persistence and requalification settings."""
        
    def add_pair(self, instrument):
        """Add a new qualified pair."""
        
    def remove_pair(self, instrument):
        """Mark a pair as disqualified."""
        
    def get_pairs_to_scan(self):
        """Get list of currently qualified pairs."""
        
    def should_requalify_pairs(self):
        """Check if requalification is needed."""
        
    def check_pair_qualification(self, instrument, data_df, strategy_func):
        """Check if a pair still qualifies based on data."""
        
    def get_stats(self):
        """Get statistics about persistent pairs."""
```

### Modified Bot Behavior

**scan_pairs_for_signals():**
```python
# If position is open and MAX_OPEN_POSITIONS == 1
if open_position_instruments and MAX_OPEN_POSITIONS == 1:
    print("SINGLE-TRADE MODE: Monitoring existing position - skipping new signal scan")
    return [], []  # No new signals to process

# Otherwise, use persistent pairs
if enable_persistent_pairs:
    # Initialize if empty
    # Requalify if interval elapsed
    # Get qualified pairs to scan
    pairs_to_scan = persistent_pairs_mgr.get_pairs_to_scan()
```

**calculate_atr_stops():**
```python
# New confidence parameter
def calculate_atr_stops(self, atr, signal, instrument, stop_multiplier=None, 
                       profit_multiplier=None, confidence=None):
    # ... existing logic ...
    
    # High confidence BUY signal adjustment
    if confidence >= HIGH_CONFIDENCE_THRESHOLD and signal == 'BUY':
        stop_mult *= HIGH_CONFIDENCE_SL_MULTIPLIER
```

## Usage Examples

### Normal Signal (confidence = 0.65)
```
Signal: BUY EUR_USD
Confidence: 0.65
ATR: 0.0010
Stop Loss: 0.5 * 0.0010 / pip_size = 5 pips
Take Profit: 1.5 * 0.0010 / pip_size = 15 pips
```

### High Confidence Signal (confidence = 0.85)
```
Signal: BUY EUR_USD
Confidence: 0.85 (>= 0.8) ✓
ATR: 0.0010
Stop Loss: 0.5 * 1.5 * 0.0010 / pip_size = 7.5 pips (loosened!)
Take Profit: 1.5 * 0.0010 / pip_size = 15 pips
```

### Persistent Pairs Lifecycle
```
Initialization:
  └─ Load from data/persistent_pairs.json
  └─ If empty, initialize from available instruments

Cycle 1 (no position):
  └─ Scan qualified pairs: [EUR_USD, GBP_USD, USD_JPY]
  └─ Find signal on EUR_USD (confidence 0.82)
  └─ Open BUY position with loosened SL

Cycle 2 (position open):
  └─ Skip signal scanning
  └─ Monitor EUR_USD position
  └─ Update trailing stops if profitable

Cycle 3 (position open):
  └─ Skip signal scanning
  └─ Monitor EUR_USD position
  └─ Position hits TP → Close trade

Cycle 4 (no position):
  └─ Check if requalification needed
  └─ If yes: recheck all pairs
      ├─ EUR_USD: Still qualified ✓
      ├─ GBP_USD: No volume → Disqualified ✗
      └─ USD_JPY: Still qualified ✓
  └─ Scan qualified pairs: [EUR_USD, USD_JPY]
  └─ Find signal on USD_JPY
```

## Benefits

1. **Reduced Complexity**: Focus on one trade simplifies risk management
2. **Better Capital Utilization**: More balance available per trade while maintaining safety
3. **Intelligent Risk Adjustment**: High confidence signals get more room to develop
4. **Consistent Pair Quality**: Only trade qualified pairs with good data
5. **Reduced API Calls**: Persistent pairs avoid repeated full scans
6. **Better Focus**: Position monitoring gets full attention when trade is open

## Configuration Summary

```python
# Single-trade strategy settings
MAX_OPEN_POSITIONS = 1
MARGIN_BUFFER = 0.50

# High confidence adjustments
HIGH_CONFIDENCE_THRESHOLD = 0.8
HIGH_CONFIDENCE_SL_MULTIPLIER = 1.5

# Persistent pairs
ENABLE_PERSISTENT_PAIRS = True
PERSISTENT_PAIRS_FILE = 'data/persistent_pairs.json'
PAIR_REQUALIFICATION_INTERVAL = 300  # seconds
MAX_PAIRS_TO_SCAN = 25
```

## Testing

Run the test suite:
```bash
python -m unittest test_single_trade_strategy -v
```

Test coverage includes:
- Persistent pairs initialization and lifecycle
- Pair qualification and disqualification
- Persistence to/from disk
- High confidence threshold configuration
- Stop loss adjustment logic
- Single-trade configuration validation

All 17 tests pass successfully ✅

## Monitoring

The bot provides detailed logging for the single-trade strategy:

```
🎯 SINGLE-TRADE MODE: Monitoring existing position EUR_USD - skipping new signal scan
🤖 BOT DECISION: Using persistent pairs (23 qualified)
🎯 High confidence BUY signal (0.85) - loosening SL: 0.50x -> 0.75x ATR
📊 Persistent pairs: 23/25 qualified
```

## Future Enhancements

Potential improvements for the single-trade strategy:
1. Dynamic confidence threshold based on market conditions
2. Position-specific requalification (recheck pairs similar to current position)
3. Machine learning for pair qualification prediction
4. Correlation-based pair selection (avoid correlated pairs)
5. Performance-based SL multiplier adjustment
