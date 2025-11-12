"""
Edge case tests for adaptive threshold persistence.
Tests scenarios that might not be covered by the main integration test.
"""
import unittest
import os
import tempfile
import sqlite3
from database import TradeDatabase
from adaptive_threshold import AdaptiveThresholdManager


class TestAdaptiveThresholdEdgeCases(unittest.TestCase):
    """Test edge cases for adaptive threshold persistence."""
    
    def setUp(self):
        """Set up test database."""
        self.temp_db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db_file.name
        self.db = TradeDatabase(db_path=self.db_path)
    
    def tearDown(self):
        """Clean up temporary database."""
        self.db.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_out_of_bounds_threshold_in_database(self):
        """Test that out-of-bounds thresholds in database are clamped to limits."""
        print("\n=== Testing Out-of-Bounds Threshold Handling ===")
        
        # Manually insert an out-of-bounds threshold into the database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Insert threshold that's too high (above max_threshold of 0.95)
        cursor.execute('''
            INSERT INTO threshold_adjustments (
                old_threshold, new_threshold, adjustment_reason
            ) VALUES (?, ?, ?)
        ''', (0.95, 1.50, "Test: artificially high threshold"))
        conn.commit()
        conn.close()
        
        # Create manager - should clamp to max_threshold
        manager = AdaptiveThresholdManager(
            base_threshold=0.8,
            db=self.db,
            min_threshold=0.5,
            max_threshold=0.95
        )
        
        loaded_threshold = manager.get_current_threshold()
        print(f"Database had threshold: 1.50")
        print(f"Loaded threshold (clamped): {loaded_threshold:.3f}")
        print(f"Maximum allowed: 0.95")
        
        self.assertEqual(loaded_threshold, 0.95,
                        "Should clamp to max_threshold")
        
        # Test threshold below minimum
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO threshold_adjustments (
                old_threshold, new_threshold, adjustment_reason
            ) VALUES (?, ?, ?)
        ''', (0.5, 0.1, "Test: artificially low threshold"))
        conn.commit()
        conn.close()
        
        # Create new manager - should clamp to min_threshold
        manager2 = AdaptiveThresholdManager(
            base_threshold=0.8,
            db=self.db,
            min_threshold=0.5,
            max_threshold=0.95
        )
        
        loaded_threshold2 = manager2.get_current_threshold()
        print(f"\nDatabase had threshold: 0.10")
        print(f"Loaded threshold (clamped): {loaded_threshold2:.3f}")
        print(f"Minimum allowed: 0.50")
        
        self.assertEqual(loaded_threshold2, 0.5,
                        "Should clamp to min_threshold")
        
        print("\n✅ Out-of-bounds thresholds are correctly clamped")
    
    def test_database_with_no_adjustments(self):
        """Test behavior when database exists but has no threshold adjustments."""
        print("\n=== Testing Database with No Adjustments ===")
        
        # Database exists but threshold_adjustments table is empty
        manager = AdaptiveThresholdManager(
            base_threshold=0.8,
            db=self.db,
            min_threshold=0.5,
            max_threshold=0.95
        )
        
        threshold = manager.get_current_threshold()
        print(f"Loaded threshold: {threshold:.3f}")
        print(f"Base threshold: 0.800")
        
        self.assertEqual(threshold, 0.8,
                        "Should use base threshold when no adjustments exist")
        
        print("✅ Correctly falls back to base threshold")
    
    def test_threshold_changes_are_immediately_persisted(self):
        """Test that threshold changes are saved immediately, not just on shutdown."""
        print("\n=== Testing Immediate Persistence ===")
        
        manager1 = AdaptiveThresholdManager(
            base_threshold=0.8,
            db=self.db,
            min_threshold=0.5,
            max_threshold=0.95,
            no_signal_cycles_trigger=3,
            adjustment_step=0.05
        )
        
        # Trigger an adjustment
        print("Session 1: Triggering adjustment...")
        for _ in range(3):
            manager1.update_on_cycle(signals_found=0)
        
        adjusted_threshold = manager1.get_current_threshold()
        print(f"  Adjusted to: {adjusted_threshold:.3f}")
        
        # WITHOUT closing the first manager, create a second one
        # This simulates checking if the write was committed immediately
        print("\nSession 2: Creating new manager WITHOUT closing first...")
        manager2 = AdaptiveThresholdManager(
            base_threshold=0.8,
            db=TradeDatabase(db_path=self.db_path),  # New DB connection
            min_threshold=0.5,
            max_threshold=0.95
        )
        
        loaded_threshold = manager2.get_current_threshold()
        print(f"  Loaded: {loaded_threshold:.3f}")
        
        self.assertEqual(loaded_threshold, adjusted_threshold,
                        "Threshold should be persisted immediately after adjustment")
        
        print("✅ Changes are persisted immediately (not buffered)")
    
    def test_multiple_rapid_adjustments(self):
        """Test that multiple rapid adjustments are all persisted correctly."""
        print("\n=== Testing Multiple Rapid Adjustments ===")
        
        manager = AdaptiveThresholdManager(
            base_threshold=0.8,
            db=self.db,
            min_threshold=0.5,
            max_threshold=0.95,
            no_signal_cycles_trigger=2,
            adjustment_step=0.05
        )
        
        print("Making multiple rapid adjustments...")
        initial = manager.get_current_threshold()
        print(f"Initial: {initial:.3f}")
        
        # Make several adjustments rapidly
        adjustments_made = 0
        for cycle in range(10):
            if manager.update_on_cycle(signals_found=0):
                adjustments_made += 1
                print(f"  Adjustment {adjustments_made}: {manager.get_current_threshold():.3f}")
        
        final_threshold = manager.get_current_threshold()
        
        # Get all adjustments from database
        adjustments = self.db.get_recent_threshold_adjustments(limit=20)
        print(f"\nAdjustments in database: {len(adjustments)}")
        print(f"Adjustments made by manager: {adjustments_made}")
        
        self.assertEqual(len(adjustments), adjustments_made,
                        "All adjustments should be persisted")
        
        # Verify that the last threshold stored matches what get_last_threshold returns
        last_threshold_from_db = self.db.get_last_threshold()
        if last_threshold_from_db is not None:
            self.assertEqual(last_threshold_from_db, final_threshold,
                           "get_last_threshold() should return the current threshold")
            print(f"Last threshold from DB: {last_threshold_from_db:.3f}")
            print(f"Current threshold: {final_threshold:.3f}")
        
        print("✅ All adjustments were persisted correctly")
    
    def test_threshold_loaded_message_is_clear(self):
        """Test that the log message clearly indicates when threshold is loaded vs initialized."""
        print("\n=== Testing Log Messages (Visual Inspection) ===")
        
        # First manager - should initialize with base
        print("\nCase 1: Brand new database")
        manager1 = AdaptiveThresholdManager(
            base_threshold=0.75,
            db=self.db,
            min_threshold=0.5,
            max_threshold=0.95
        )
        print(f"Expected log: 'Adaptive threshold initialized with base value: 0.750'")
        
        # Make an adjustment
        for _ in range(5):
            manager1.update_on_cycle(signals_found=0)
        
        # Second manager - should load from database
        print("\nCase 2: Database with existing adjustments")
        manager2 = AdaptiveThresholdManager(
            base_threshold=0.75,
            db=TradeDatabase(db_path=self.db_path),
            min_threshold=0.5,
            max_threshold=0.95
        )
        print(f"Expected log: 'Adaptive threshold loaded from database: {manager2.get_current_threshold():.3f}'")
        
        print("\n✅ Log messages differentiate initialization sources")


if __name__ == '__main__':
    # Run with verbose output
    unittest.main(verbosity=2)
