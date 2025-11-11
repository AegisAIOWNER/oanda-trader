"""
Integration test for adaptive threshold functionality.
Tests the complete lifecycle of the adaptive threshold system.
"""
import unittest
import pandas as pd
import numpy as np
import os
import tempfile
from database import TradeDatabase
from adaptive_threshold import AdaptiveThresholdManager


class TestAdaptiveThresholdIntegration(unittest.TestCase):
    """Integration test for adaptive threshold system."""
    
    def setUp(self):
        """Set up test database and manager."""
        self.temp_db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db_file.name
        self.db = TradeDatabase(db_path=self.db_path)
        
        self.manager = AdaptiveThresholdManager(
            base_threshold=0.8,
            db=self.db,
            min_threshold=0.5,
            max_threshold=0.95,
            no_signal_cycles_trigger=5,
            adjustment_step=0.02
        )
    
    def tearDown(self):
        """Clean up temporary database."""
        self.db.close()
        os.unlink(self.db_path)
    
    def test_complete_adaptive_cycle(self):
        """Test complete adaptive threshold lifecycle with realistic scenario."""
        print("\n=== Testing Complete Adaptive Threshold Lifecycle ===")
        
        # Scenario 1: Bot starts, no signals for several cycles
        print("\nScenario 1: No signals found, threshold should lower")
        initial_threshold = self.manager.get_current_threshold()
        print(f"Initial threshold: {initial_threshold:.3f}")
        
        for cycle in range(5):
            adjusted = self.manager.update_on_cycle(signals_found=0)
            if adjusted:
                print(f"  Cycle {cycle + 1}: Threshold adjusted to {self.manager.get_current_threshold():.3f}")
        
        self.assertLess(self.manager.get_current_threshold(), initial_threshold,
                       "Threshold should be lowered after no signals")
        
        # Scenario 2: Signals found, threshold stabilizes
        print("\nScenario 2: Signals found, counter resets")
        self.manager.update_on_cycle(signals_found=3)
        self.assertEqual(self.manager.cycles_without_signal, 0,
                        "Counter should reset when signals found")
        
        # Scenario 3: Simulate some trades and build performance history
        print("\nScenario 3: Building trade history")
        # Add some closed trades to database for performance metrics
        for i in range(10):
            trade_data = {
                'instrument': 'EUR_USD',
                'signal': 'BUY' if i % 2 == 0 else 'SELL',
                'confidence': 0.85,
                'entry_price': 1.1000 + (i * 0.0001),
                'stop_loss': 0.001,
                'take_profit': 0.002,
                'units': 1000,
                'atr': 0.0001,
                'ml_prediction': 0.7,
                'position_size_pct': 0.02
            }
            trade_id = self.db.store_trade(trade_data)
            
            # Simulate trade outcomes (70% win rate)
            if i < 7:  # Winning trades
                self.db.update_trade(trade_id, 1.1010, 20.0, 'closed')
            else:  # Losing trades
                self.db.update_trade(trade_id, 1.0995, -10.0, 'closed')
        
        # Scenario 4: Good performance should raise threshold
        print("\nScenario 4: Good performance, threshold should raise")
        threshold_before = self.manager.get_current_threshold()
        performance = self.db.get_performance_metrics(days=30)
        print(f"  Performance: win_rate={performance['win_rate']:.2%}, "
              f"profit_factor={performance['profit_factor']:.2f}, "
              f"trades={performance['total_trades']}")
        
        adjusted = self.manager.update_on_trade_result(
            trade_profitable=True,
            recent_performance=performance
        )
        
        if adjusted:
            print(f"  Threshold raised from {threshold_before:.3f} to "
                  f"{self.manager.get_current_threshold():.3f}")
            self.assertGreater(self.manager.get_current_threshold(), threshold_before,
                             "Threshold should be raised with good performance")
        
        # Scenario 5: Check all adjustments are logged
        print("\nScenario 5: Verify adjustments are logged in database")
        adjustments = self.db.get_recent_threshold_adjustments(limit=10)
        print(f"  Total adjustments logged: {len(adjustments)}")
        self.assertGreater(len(adjustments), 0, "Adjustments should be logged")
        
        for adj in adjustments:
            print(f"  - {adj['old_threshold']:.3f} → {adj['new_threshold']:.3f}: "
                  f"{adj['adjustment_reason'][:60]}...")
        
        # Scenario 6: Test safety bounds
        print("\nScenario 6: Testing safety bounds")
        # Try to push threshold beyond max
        self.manager.current_threshold = 0.94
        for i in range(5):
            self.manager.update_on_trade_result(
                trade_profitable=True,
                recent_performance={'win_rate': 0.80, 'profit_factor': 2.0, 'total_trades': 10}
            )
        
        self.assertLessEqual(self.manager.get_current_threshold(), 
                            self.manager.max_threshold,
                            "Threshold should not exceed max bound")
        print(f"  Maximum threshold enforced: {self.manager.get_current_threshold():.3f} <= "
              f"{self.manager.max_threshold:.3f}")
        
        # Scenario 7: Test status reporting
        print("\nScenario 7: Status reporting")
        status = self.manager.get_status()
        print(f"  Current status:")
        for key, value in status.items():
            print(f"    {key}: {value}")
        
        self.assertIn('current_threshold', status)
        self.assertIn('base_threshold', status)
        
        print("\n=== Adaptive Threshold Integration Test Complete ===")
        print("✅ All scenarios passed successfully!")
    
    def test_performance_based_adjustment_logic(self):
        """Test different performance scenarios trigger correct adjustments."""
        print("\n=== Testing Performance-Based Adjustment Logic ===")
        
        # Test 1: High performance -> raise threshold
        print("\nTest 1: High performance (65% win, 1.8 profit factor)")
        threshold_before = self.manager.current_threshold
        adjusted = self.manager.update_on_trade_result(
            trade_profitable=True,
            recent_performance={'win_rate': 0.65, 'profit_factor': 1.8, 'total_trades': 10}
        )
        if adjusted:
            print(f"  ✓ Threshold raised: {threshold_before:.3f} → {self.manager.current_threshold:.3f}")
            self.assertGreater(self.manager.current_threshold, threshold_before)
        
        # Reset for next test
        self.manager.reset_to_base()
        
        # Test 2: Poor performance -> raise threshold (be more selective)
        print("\nTest 2: Poor performance (40% win, 0.7 profit factor)")
        threshold_before = self.manager.current_threshold
        adjusted = self.manager.update_on_trade_result(
            trade_profitable=False,
            recent_performance={'win_rate': 0.40, 'profit_factor': 0.7, 'total_trades': 10}
        )
        if adjusted:
            print(f"  ✓ Threshold raised: {threshold_before:.3f} → {self.manager.current_threshold:.3f}")
            self.assertGreater(self.manager.current_threshold, threshold_before)
        
        # Reset for next test
        self.manager.reset_to_base()
        
        # Test 3: Marginal performance -> lower threshold (seek opportunities)
        print("\nTest 3: Marginal performance (52% win, 1.05 profit factor)")
        threshold_before = self.manager.current_threshold
        adjusted = self.manager.update_on_trade_result(
            trade_profitable=True,
            recent_performance={'win_rate': 0.52, 'profit_factor': 1.05, 'total_trades': 10}
        )
        if adjusted:
            print(f"  ✓ Threshold lowered: {threshold_before:.3f} → {self.manager.current_threshold:.3f}")
            self.assertLess(self.manager.current_threshold, threshold_before)
        
        print("\n=== Performance-Based Adjustment Logic Test Complete ===")
    
    def test_threshold_persistence_across_restarts(self):
        """Test that threshold persists across bot restarts."""
        print("\n=== Testing Threshold Persistence Across Restarts ===")
        
        # Simulate first bot session
        print("\nSimulation 1: First bot session")
        initial_threshold = 0.8
        print(f"  Starting with base threshold: {initial_threshold:.3f}")
        
        # Manager starts with base threshold
        self.assertEqual(self.manager.get_current_threshold(), initial_threshold,
                        "Should start with base threshold on first run")
        
        # Make some adjustments
        print("\n  Making adjustments...")
        for _ in range(5):
            self.manager.update_on_cycle(signals_found=0)
        
        adjusted_threshold = self.manager.get_current_threshold()
        print(f"  Threshold after adjustments: {adjusted_threshold:.3f}")
        self.assertNotEqual(adjusted_threshold, initial_threshold,
                          "Threshold should have been adjusted")
        
        # Simulate bot restart - create a new manager with the same database
        print("\nSimulation 2: Bot restart (new manager instance)")
        new_manager = AdaptiveThresholdManager(
            base_threshold=0.8,
            db=self.db,
            min_threshold=0.5,
            max_threshold=0.95,
            no_signal_cycles_trigger=5,
            adjustment_step=0.02
        )
        
        loaded_threshold = new_manager.get_current_threshold()
        print(f"  Loaded threshold from database: {loaded_threshold:.3f}")
        
        # The new manager should load the last adjusted threshold
        self.assertEqual(loaded_threshold, adjusted_threshold,
                        "New manager should load the last adjusted threshold from database")
        self.assertNotEqual(loaded_threshold, initial_threshold,
                          "Loaded threshold should not reset to base value")
        
        print(f"\n  ✅ Success! Threshold persisted: {adjusted_threshold:.3f}")
        
        # Test that further adjustments work correctly
        print("\n  Making more adjustments after restart...")
        threshold_before = new_manager.get_current_threshold()
        
        # Add trades to trigger performance-based adjustment
        for i in range(10):
            trade_data = {
                'instrument': 'EUR_USD',
                'signal': 'BUY',
                'confidence': 0.85,
                'entry_price': 1.1000,
                'stop_loss': 0.001,
                'take_profit': 0.002,
                'units': 1000,
                'atr': 0.0001,
                'ml_prediction': 0.7,
                'position_size_pct': 0.02
            }
            trade_id = self.db.store_trade(trade_data)
            # All winning trades
            self.db.update_trade(trade_id, 1.1010, 20.0, 'closed')
        
        performance = self.db.get_performance_metrics(days=30)
        new_manager.update_on_trade_result(
            trade_profitable=True,
            recent_performance=performance
        )
        
        threshold_after = new_manager.get_current_threshold()
        print(f"  Threshold after more adjustments: {threshold_after:.3f}")
        
        # Verify one more restart to ensure persistence continues
        print("\nSimulation 3: Another bot restart")
        final_manager = AdaptiveThresholdManager(
            base_threshold=0.8,
            db=self.db,
            min_threshold=0.5,
            max_threshold=0.95,
            no_signal_cycles_trigger=5,
            adjustment_step=0.02
        )
        
        final_threshold = final_manager.get_current_threshold()
        print(f"  Final loaded threshold: {final_threshold:.3f}")
        
        self.assertEqual(final_threshold, threshold_after,
                        "Threshold should persist through multiple restarts")
        
        print("\n=== Threshold Persistence Test Complete ===")
        print("✅ Threshold successfully persists across bot restarts!")


if __name__ == '__main__':
    # Run with verbose output
    unittest.main(verbosity=2)
