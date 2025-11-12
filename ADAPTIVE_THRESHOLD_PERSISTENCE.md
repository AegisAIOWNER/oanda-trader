# Adaptive Threshold Persistence

## Overview

The Oanda Trading Bot implements **automatic persistence** of the adaptive confidence threshold. This ensures that the bot remembers its learned threshold adjustments across restarts, enabling continuous optimization without resetting to the base configuration value.

## How It Works

### Persistence Mechanism

1. **Saving**: Every time the adaptive threshold is adjusted, the change is immediately saved to the `threshold_adjustments` table in the SQLite database (`trades.db`).

2. **Loading**: When the bot starts (or when `AdaptiveThresholdManager` is initialized), it automatically loads the most recent threshold value from the database.

3. **Fallback**: If no previous adjustments exist (e.g., first run), the bot uses the base threshold from `config.py`.

### Database Schema

```sql
CREATE TABLE threshold_adjustments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    old_threshold REAL NOT NULL,
    new_threshold REAL NOT NULL,
    adjustment_reason TEXT NOT NULL,
    cycles_without_signal INTEGER DEFAULT 0,
    recent_win_rate REAL,
    recent_profit_factor REAL,
    total_trades_analyzed INTEGER DEFAULT 0
)
```

### Code Implementation

#### Loading on Startup

Located in `adaptive_threshold.py`, lines 41-52:

```python
# Load last threshold from database if available
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
```

#### Saving Adjustments

Located in `adaptive_threshold.py`, lines 217-235:

Every adjustment method (`_lower_threshold_for_signal_frequency()`, `_raise_threshold_for_performance()`, etc.) calls `_log_adjustment()`, which:

1. Logs the change to the console
2. Stores the adjustment in the database via `db.store_threshold_adjustment()`

```python
def _log_adjustment(self, old_threshold, new_threshold, reason, ...):
    """Log threshold adjustment to database and logger."""
    logging.info(f"🤖 ADAPTIVE THRESHOLD: {old_threshold:.3f} → {new_threshold:.3f}")
    logging.info(f"   Reason: {reason}")
    
    if self.db:
        adjustment_data = {
            'old_threshold': old_threshold,
            'new_threshold': new_threshold,
            'adjustment_reason': reason,
            # ... additional context
        }
        self.db.store_threshold_adjustment(adjustment_data)
```

## Behavior Examples

### Example 1: First Startup (No Database)

```
Bot starts → No database exists → Creates new database
AdaptiveThresholdManager initializes → No adjustments in database
Uses base threshold from config: 0.8
```

Log output:
```
Adaptive threshold initialized with base value: 0.800
```

### Example 2: Restart After Adjustments

```
Bot had previously lowered threshold to 0.76 → Bot restarts
AdaptiveThresholdManager initializes → Loads from database
Uses persisted threshold: 0.76 (NOT config base of 0.8)
```

Log output:
```
Adaptive threshold loaded from database: 0.760
```

### Example 3: Multiple Restarts

```
Session 1: 0.8 → adjusted to 0.76 → Bot stops
Session 2: Loads 0.76 → adjusted to 0.82 → Bot stops  
Session 3: Loads 0.82 → continues from there
```

Each session builds upon the previous session's learned threshold.

## Safety Features

### Bounds Checking

Even if the database contains an out-of-bounds threshold (e.g., from manual editing or a bug), the loaded value is clamped to the configured limits:

```python
self.current_threshold = max(min_threshold, min(max_threshold, last_threshold))
```

- **min_threshold**: Default 0.5 (configurable via `ADAPTIVE_MIN_THRESHOLD`)
- **max_threshold**: Default 0.95 (configurable via `ADAPTIVE_MAX_THRESHOLD`)

### Immediate Persistence

Adjustments are saved immediately to the database (not buffered), ensuring that even if the bot crashes, the most recent adjustment is preserved.

## Configuration

### Disabling Persistence

To disable adaptive threshold entirely (and use a fixed threshold):

```python
# In config.py
ENABLE_ADAPTIVE_THRESHOLD = False
```

or via CLI:

```bash
python cli.py start --no-adaptive-threshold
```

### Resetting Threshold

To manually reset the threshold to the base value:

```python
manager = AdaptiveThresholdManager(...)
manager.reset_to_base()  # Resets to base_threshold and logs the change
```

This also saves the reset to the database, so subsequent restarts will use the base value.

### Database Location

The database is stored at `./trades.db` by default. To use a different location:

```python
db = TradeDatabase(db_path='/path/to/custom_trades.db')
manager = AdaptiveThresholdManager(base_threshold=0.8, db=db)
```

## Testing

### Integration Tests

Run the comprehensive integration tests:

```bash
python test_adaptive_integration.py
```

This includes:
- ✅ Threshold persistence across restarts
- ✅ Multiple restart scenarios
- ✅ Performance-based adjustments
- ✅ Signal frequency adjustments
- ✅ Database logging

### Edge Case Tests

Run additional edge case tests:

```bash
python test_adaptive_threshold_edge_cases.py
```

This covers:
- ✅ Out-of-bounds threshold clamping
- ✅ Brand new database behavior
- ✅ Immediate persistence (no buffering)
- ✅ Multiple rapid adjustments
- ✅ Log message clarity

## Monitoring

### View Adjustment History

Query the database to see all threshold adjustments:

```python
from database import TradeDatabase

db = TradeDatabase()
adjustments = db.get_recent_threshold_adjustments(limit=50)

for adj in adjustments:
    print(f"{adj['timestamp']}: {adj['old_threshold']:.3f} → "
          f"{adj['new_threshold']:.3f}")
    print(f"  Reason: {adj['adjustment_reason']}")
```

### Current Threshold Status

Check the current threshold and its history:

```python
manager = AdaptiveThresholdManager(base_threshold=0.8, db=db)
status = manager.get_status()

print(f"Current threshold: {status['current_threshold']:.3f}")
print(f"Base threshold: {status['base_threshold']:.3f}")
print(f"Cycles without signal: {status['cycles_without_signal']}")
```

## Benefits

1. **Continuous Learning**: The bot builds upon its previous adjustments, not starting from scratch each time.

2. **Adaptive to Market Conditions**: If the bot has learned that a lower threshold works better in current conditions, it maintains that learning.

3. **Transparent**: All adjustments are logged with reasons, allowing you to understand why the threshold changed.

4. **Safe**: Bounds checking ensures the threshold stays within reasonable limits.

5. **Resilient**: Immediate persistence means even crashes don't lose the most recent learning.

## Troubleshooting

### Threshold Not Loading

1. Check that `ENABLE_ADAPTIVE_THRESHOLD = True` in config
2. Verify database exists: `ls -lh trades.db`
3. Check for database errors in logs
4. Verify the database has adjustments: `sqlite3 trades.db "SELECT * FROM threshold_adjustments ORDER BY id DESC LIMIT 5;"`

### Unexpected Threshold Value

1. Check adjustment history: `db.get_recent_threshold_adjustments()`
2. Look for the adjustment reason in the logs
3. Verify it's not being clamped to min/max bounds
4. Check for manual resets in the adjustment history

### Want to Start Fresh

Delete the database file:

```bash
rm trades.db
```

The bot will create a new database and start with the base threshold on the next run.

## Related Files

- **Implementation**: `adaptive_threshold.py`
- **Database**: `database.py`
- **Configuration**: `config.py`
- **Integration Tests**: `test_adaptive_integration.py`
- **Edge Case Tests**: `test_adaptive_threshold_edge_cases.py`
- **Bot Integration**: `bot.py` (lines 80-92)
