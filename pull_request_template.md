# This PR fixes the STOP_LOSS_ON_FILL_LOSS errors by improving stop loss distance calculation and rounding. It also configures the bot for small balance (~19 GBP) by using only affordable major FX pairs, adjusting risk settings for faster profits, and optimizing for scalping with minimal margin requirements.

## Key changes:
- Disable dynamic instruments and affordability filter to focus on cheap pairs
- Increase risk per trade to 5% for faster results
- Lower confidence threshold and faster adaptive adjustments
- Add debug logging for stop loss validation
- Single trade mode for small balance
- Faster cycle intervals (60s instead of 120s)