# Adaptive Threshold - Quick Reference Guide

## TL;DR

✅ **The bot DOES remember its adaptive threshold across restarts**
- Threshold adjustments are saved to database automatically
- On restart, bot loads the last adjusted threshold (NOT config base value)
- No manual configuration needed - works out of the box

## Quick Test

Want to verify it's working? Run this:

```bash
python demo_threshold_persistence.py
```

This demonstrates the feature in action with 3 simulated bot restarts.

## How To Check Current Threshold

```python
from database import TradeDatabase
from adaptive_threshold import AdaptiveThresholdManager

db = TradeDatabase()
manager = AdaptiveThresholdManager(base_threshold=0.8, db=db)

print(f"Current threshold: {manager.get_current_threshold():.3f}")
print(f"Base config: {manager.base_threshold:.3f}")

# View adjustment history
adjustments = db.get_recent_threshold_adjustments(limit=10)
for adj in adjustments:
    print(f"{adj['timestamp']}: {adj['old_threshold']:.3f} → {adj['new_threshold']:.3f}")
```

## Common Questions

### Q: Does the bot reset to config value on restart?
**A**: No. It loads the last adjusted threshold from the database.

### Q: Where is the threshold stored?
**A**: In `trades.db` database, table `threshold_adjustments`.

### Q: Can I see the adjustment history?
**A**: Yes. Query the database or use `db.get_recent_threshold_adjustments()`.

### Q: What if I want to reset to base threshold?
**A**: Delete the database file (`rm trades.db`) or call `manager.reset_to_base()`.

### Q: How do I disable adaptive threshold?
**A**: Set `ENABLE_ADAPTIVE_THRESHOLD = False` in `config.py` or use `--no-adaptive-threshold` flag.

### Q: What if the database gets corrupted?
**A**: Out-of-bounds values are automatically clamped to min/max limits on load.

## Log Messages To Look For

**First startup (no database):**
```
Adaptive threshold initialized with base value: 0.800
```

**Restart (with database):**
```
Adaptive threshold loaded from database: 0.760
```

**When threshold adjusts:**
```
🤖 ADAPTIVE THRESHOLD: 0.800 → 0.780
   Reason: Lowered threshold after 5 cycles without signals to increase signal frequency
```

## Files To Reference

- **Complete Documentation**: `ADAPTIVE_THRESHOLD_PERSISTENCE.md`
- **Verification Report**: `VERIFICATION_SUMMARY.md`
- **Tests**: `test_adaptive_integration.py`, `test_adaptive_threshold_edge_cases.py`
- **Demo**: `demo_threshold_persistence.py`
- **Code**: `adaptive_threshold.py`, `database.py`

## Troubleshooting

**Problem**: Threshold seems to reset on restart
1. Check that `ENABLE_ADAPTIVE_THRESHOLD = True` in config
2. Verify database file exists: `ls -lh trades.db`
3. Check for database errors in logs
4. Run the demo script to confirm feature works

**Problem**: Want to start fresh
1. Stop the bot
2. Delete database: `rm trades.db`
3. Restart bot - will use base config value

## Configuration Options

In `config.py`:

```python
ENABLE_ADAPTIVE_THRESHOLD = True      # Enable/disable feature
CONFIDENCE_THRESHOLD = 0.8            # Base threshold (used on first startup)
ADAPTIVE_MIN_THRESHOLD = 0.5          # Minimum allowed value
ADAPTIVE_MAX_THRESHOLD = 0.95         # Maximum allowed value
ADAPTIVE_NO_SIGNAL_CYCLES = 5         # Cycles before lowering threshold
ADAPTIVE_ADJUSTMENT_STEP = 0.02       # How much to adjust by (2%)
```

## Need Help?

1. Read the full documentation: `ADAPTIVE_THRESHOLD_PERSISTENCE.md`
2. Check the verification report: `VERIFICATION_SUMMARY.md`
3. Run the demo: `python demo_threshold_persistence.py`
4. Check test examples: `test_adaptive_integration.py`

---

**Status**: ✅ Fully implemented and working
**Version**: 1.0
**Last Updated**: 2025-11-12
