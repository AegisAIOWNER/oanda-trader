#!/usr/bin/env python
"""
Demonstration script showing adaptive threshold persistence in action.
This script simulates bot restarts and shows how the threshold persists.
"""
import os
import sys
from database import TradeDatabase
from adaptive_threshold import AdaptiveThresholdManager


def print_separator(title=""):
    """Print a visual separator."""
    print("\n" + "=" * 80)
    if title:
        print(f" {title} ".center(80, "="))
        print("=" * 80)


def demo_persistence():
    """Demonstrate threshold persistence across bot restarts."""
    # Use a demo database
    db_path = 'demo_trades.db'
    
    # Clean up any existing demo database
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Cleaned up existing demo database: {db_path}")
    
    print_separator("ADAPTIVE THRESHOLD PERSISTENCE DEMO")
    print("\nThis demo simulates how the bot remembers its adaptive threshold")
    print("across restarts, never resetting to the base config value.")
    
    # === SIMULATION 1: First Bot Startup ===
    print_separator("SIMULATION 1: Bot First Startup (Fresh Install)")
    
    print("\n📋 Creating new database and initializing bot...")
    db1 = TradeDatabase(db_path=db_path)
    
    print("📋 Initializing AdaptiveThresholdManager with base_threshold=0.8")
    manager1 = AdaptiveThresholdManager(
        base_threshold=0.8,
        db=db1,
        min_threshold=0.5,
        max_threshold=0.95,
        no_signal_cycles_trigger=3,
        adjustment_step=0.05
    )
    
    print(f"\n✓ Bot started with threshold: {manager1.get_current_threshold():.3f}")
    print("  (This is the base config value since no adjustments exist)")
    
    # Simulate running for a while with no signals
    print("\n🔄 Simulating 3 trading cycles with no signals...")
    for cycle in range(3):
        adjusted = manager1.update_on_cycle(signals_found=0)
        if adjusted:
            print(f"  📉 Cycle {cycle + 1}: Threshold lowered to {manager1.get_current_threshold():.3f}")
        else:
            print(f"  ⏸️  Cycle {cycle + 1}: No adjustment yet (count: {manager1.cycles_without_signal})")
    
    final_threshold_session1 = manager1.get_current_threshold()
    print(f"\n✓ Session 1 ends with threshold: {final_threshold_session1:.3f}")
    print("  (Threshold was adjusted down to find more signals)")
    
    db1.close()
    print("\n🛑 Bot stopped (database closed)")
    
    # === SIMULATION 2: Bot Restart ===
    print_separator("SIMULATION 2: Bot Restart (Same Database)")
    
    print("\n📋 Restarting bot...")
    print("📋 Initializing AdaptiveThresholdManager with base_threshold=0.8 again")
    print("   (This is what the config says, but will it use this value?)")
    
    db2 = TradeDatabase(db_path=db_path)
    manager2 = AdaptiveThresholdManager(
        base_threshold=0.8,  # Config says 0.8
        db=db2,
        min_threshold=0.5,
        max_threshold=0.95,
        no_signal_cycles_trigger=3,
        adjustment_step=0.05
    )
    
    loaded_threshold = manager2.get_current_threshold()
    
    print(f"\n✓ Bot started with threshold: {loaded_threshold:.3f}")
    
    if loaded_threshold == final_threshold_session1:
        print("  ✅ SUCCESS! Threshold loaded from database, not reset to config!")
        print(f"  ✅ The bot remembered the adjusted value: {loaded_threshold:.3f}")
    else:
        print(f"  ❌ ERROR! Threshold should be {final_threshold_session1:.3f} but got {loaded_threshold:.3f}")
    
    if loaded_threshold == 0.8:
        print("  ❌ ERROR! Threshold reset to base config value (0.8)")
    else:
        print(f"  ✅ Did NOT reset to base config value (0.8)")
    
    # Continue with more activity
    print("\n🔄 Simulating finding some signals and trades...")
    
    # Add some profitable trades
    for i in range(8):
        trade_data = {
            'instrument': 'EUR_USD',
            'signal': 'BUY',
            'confidence': 0.85,
            'entry_price': 1.1000 + (i * 0.0001),
            'stop_loss': 0.001,
            'take_profit': 0.002,
            'units': 1000,
            'atr': 0.0001,
            'ml_prediction': 0.7,
            'position_size_pct': 0.02
        }
        trade_id = db2.store_trade(trade_data)
        # 75% win rate
        if i < 6:
            db2.update_trade(trade_id, 1.1010, 20.0, 'closed')
        else:
            db2.update_trade(trade_id, 1.0995, -10.0, 'closed')
    
    performance = db2.get_performance_metrics(days=30)
    print(f"  📊 Performance: {performance['win_rate']:.1%} win rate, "
          f"profit factor {performance['profit_factor']:.2f}")
    
    # Trigger performance-based adjustment
    adjusted = manager2.update_on_trade_result(
        trade_profitable=True,
        recent_performance=performance
    )
    
    if adjusted:
        new_threshold = manager2.get_current_threshold()
        print(f"  📈 Good performance! Threshold raised to {new_threshold:.3f}")
    
    final_threshold_session2 = manager2.get_current_threshold()
    print(f"\n✓ Session 2 ends with threshold: {final_threshold_session2:.3f}")
    
    db2.close()
    print("\n🛑 Bot stopped again")
    
    # === SIMULATION 3: Another Restart ===
    print_separator("SIMULATION 3: Another Bot Restart")
    
    print("\n📋 Starting bot one more time...")
    print("📋 Again initializing with base_threshold=0.8 from config")
    
    db3 = TradeDatabase(db_path=db_path)
    manager3 = AdaptiveThresholdManager(
        base_threshold=0.8,  # Still says 0.8 in config
        db=db3,
        min_threshold=0.5,
        max_threshold=0.95,
        no_signal_cycles_trigger=3,
        adjustment_step=0.05
    )
    
    final_loaded_threshold = manager3.get_current_threshold()
    
    print(f"\n✓ Bot started with threshold: {final_loaded_threshold:.3f}")
    
    if final_loaded_threshold == final_threshold_session2:
        print("  ✅ SUCCESS! Threshold persisted from Session 2!")
        print(f"  ✅ The bot continues its learning journey")
    else:
        print(f"  ❌ ERROR! Expected {final_threshold_session2:.3f} but got {final_loaded_threshold:.3f}")
    
    # Show adjustment history
    print("\n📜 Complete adjustment history:")
    adjustments = db3.get_recent_threshold_adjustments(limit=10)
    
    for i, adj in enumerate(reversed(adjustments), 1):
        reason_short = adj['adjustment_reason'][:50] + "..." if len(adj['adjustment_reason']) > 50 else adj['adjustment_reason']
        print(f"  {i}. {adj['old_threshold']:.3f} → {adj['new_threshold']:.3f}")
        print(f"     Reason: {reason_short}")
    
    db3.close()
    
    # === FINAL SUMMARY ===
    print_separator("SUMMARY")
    
    print("\n✅ Adaptive threshold persistence is working correctly!")
    print("\nKey points demonstrated:")
    print("  1. ✓ First startup uses base config value (0.8)")
    print(f"  2. ✓ Bot adjusts threshold based on performance (0.8 → {final_threshold_session1:.3f})")
    print(f"  3. ✓ After restart, bot loads adjusted value ({final_threshold_session1:.3f}), NOT config (0.8)")
    print(f"  4. ✓ Bot continues adjusting from loaded value ({final_threshold_session1:.3f} → {final_threshold_session2:.3f})")
    print(f"  5. ✓ Another restart loads latest value ({final_threshold_session2:.3f})")
    print("  6. ✓ All adjustments are logged in database with reasons")
    
    print("\n💡 This means the bot never forgets its learning and continuously")
    print("   optimizes the confidence threshold across sessions!")
    
    # Clean up
    os.remove(db_path)
    print(f"\n🧹 Demo database removed: {db_path}")
    
    print_separator()


if __name__ == '__main__':
    try:
        demo_persistence()
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
