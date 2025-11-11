"""
Unit tests for volatility detection and conditional strategy adjustments.
"""
import unittest
import numpy as np
from volatility_detector import VolatilityDetector
from adaptive_threshold import AdaptiveThresholdManager
from database import TradeDatabase
import tempfile
import os


class TestVolatilityDetector(unittest.TestCase):
    """Test volatility detection functionality."""
    
    def setUp(self):
        """Create volatility detector for testing."""
        self.detector = VolatilityDetector(
            low_threshold=0.0005,
            normal_threshold=0.0015,
            adjustment_mode='adaptive',
            atr_window=10
        )
    
    def test_initialization(self):
        """Test volatility detector initialization."""
        self.assertEqual(self.detector.low_threshold, 0.0005)
        self.assertEqual(self.detector.normal_threshold, 0.0015)
        self.assertEqual(self.detector.adjustment_mode, 'adaptive')
        self.assertEqual(self.detector.current_volatility_state, 'UNKNOWN')
    
    def test_detect_low_volatility(self):
        """Test detection of low volatility conditions."""
        # Create ATR readings below low threshold
        low_atrs = [0.0003, 0.0004, 0.0003, 0.0004, 0.0003]
        
        result = self.detector.detect_volatility(low_atrs)
        
        self.assertEqual(result['state'], 'LOW')
        self.assertLess(result['avg_atr'], self.detector.low_threshold)
        self.assertEqual(result['readings_count'], 5)
        self.assertGreater(result['confidence'], 0.0)
        self.assertEqual(self.detector.consecutive_low_volatility_cycles, 1)
    
    def test_detect_normal_volatility(self):
        """Test detection of normal volatility conditions."""
        # Create ATR readings between low and normal threshold
        normal_atrs = [0.0008, 0.0009, 0.0010, 0.0011, 0.0009]
        
        result = self.detector.detect_volatility(normal_atrs)
        
        self.assertEqual(result['state'], 'NORMAL')
        self.assertGreaterEqual(result['avg_atr'], self.detector.low_threshold)
        self.assertLess(result['avg_atr'], self.detector.normal_threshold)
        self.assertEqual(self.detector.consecutive_low_volatility_cycles, 0)
    
    def test_detect_high_volatility(self):
        """Test detection of high volatility conditions."""
        # Create ATR readings above normal threshold
        high_atrs = [0.0020, 0.0025, 0.0022, 0.0023, 0.0021]
        
        result = self.detector.detect_volatility(high_atrs)
        
        self.assertEqual(result['state'], 'HIGH')
        self.assertGreaterEqual(result['avg_atr'], self.detector.normal_threshold)
        self.assertEqual(self.detector.consecutive_low_volatility_cycles, 0)
    
    def test_consecutive_low_volatility_tracking(self):
        """Test tracking of consecutive low volatility cycles."""
        low_atrs = [0.0003, 0.0004, 0.0003]
        
        # First low cycle
        self.detector.detect_volatility(low_atrs)
        self.assertEqual(self.detector.consecutive_low_volatility_cycles, 1)
        
        # Second low cycle
        self.detector.detect_volatility(low_atrs)
        self.assertEqual(self.detector.consecutive_low_volatility_cycles, 2)
        
        # Third low cycle
        self.detector.detect_volatility(low_atrs)
        self.assertEqual(self.detector.consecutive_low_volatility_cycles, 3)
        
        # Now high volatility should reset counter
        high_atrs = [0.0020, 0.0025, 0.0022]
        self.detector.detect_volatility(high_atrs)
        self.assertEqual(self.detector.consecutive_low_volatility_cycles, 0)
    
    def test_threshold_adjustment_in_low_volatility(self):
        """Test aggressive threshold lowering in low volatility."""
        # Simulate low volatility
        low_atrs = [0.0003, 0.0004, 0.0003]
        self.detector.detect_volatility(low_atrs)
        self.detector.detect_volatility(low_atrs)  # 2 consecutive
        
        current_threshold = 0.80
        base_step = 0.02
        
        adjustment = self.detector.get_threshold_adjustment(current_threshold, base_step)
        
        # In low volatility with adaptive mode, step should be increased
        self.assertGreater(adjustment['adjusted_step'], base_step)
        self.assertLess(adjustment['adjusted_threshold'], current_threshold)
    
    def test_threshold_adjustment_in_normal_volatility(self):
        """Test no aggressive adjustment in normal volatility."""
        # Simulate normal volatility
        normal_atrs = [0.0008, 0.0009, 0.0010]
        self.detector.detect_volatility(normal_atrs)
        
        current_threshold = 0.80
        base_step = 0.02
        
        adjustment = self.detector.get_threshold_adjustment(current_threshold, base_step)
        
        # In normal volatility, no adjustment should be made
        self.assertEqual(adjustment['adjusted_step'], base_step)
        self.assertEqual(adjustment['adjusted_threshold'], current_threshold)
    
    def test_stop_profit_adjustment_in_low_volatility(self):
        """Test stop-loss and take-profit widening in low volatility."""
        # Simulate low volatility
        low_atrs = [0.0003, 0.0004, 0.0003]
        self.detector.detect_volatility(low_atrs)
        
        base_stop = 1.5
        base_profit = 2.5
        
        adjustment = self.detector.get_stop_profit_adjustment(base_stop, base_profit)
        
        # In low volatility with adaptive or widen_stops mode, multipliers should increase
        self.assertGreater(adjustment['stop_multiplier'], base_stop)
        self.assertGreater(adjustment['profit_multiplier'], base_profit)
    
    def test_stop_profit_no_adjustment_in_normal_volatility(self):
        """Test no stop-loss/take-profit adjustment in normal volatility."""
        # Simulate normal volatility
        normal_atrs = [0.0008, 0.0009, 0.0010]
        self.detector.detect_volatility(normal_atrs)
        
        base_stop = 1.5
        base_profit = 2.5
        
        adjustment = self.detector.get_stop_profit_adjustment(base_stop, base_profit)
        
        # In normal volatility, no adjustment should be made
        self.assertEqual(adjustment['stop_multiplier'], base_stop)
        self.assertEqual(adjustment['profit_multiplier'], base_profit)
    
    def test_cycle_skip_in_low_volatility(self):
        """Test cycle skipping in low volatility with skip_cycles mode."""
        # Create detector with skip_cycles mode
        skip_detector = VolatilityDetector(
            low_threshold=0.0005,
            normal_threshold=0.0015,
            adjustment_mode='skip_cycles',
            atr_window=10
        )
        
        low_atrs = [0.0003, 0.0004, 0.0003]
        
        # Need 3+ consecutive low cycles to trigger skip
        skip_detector.detect_volatility(low_atrs)
        skip_detector.detect_volatility(low_atrs)
        skip_detector.detect_volatility(low_atrs)
        
        skip_decision = skip_detector.should_skip_cycle()
        
        self.assertTrue(skip_decision['skip'])
        self.assertIn('consecutive', skip_decision['reason'].lower())
    
    def test_no_cycle_skip_with_wrong_mode(self):
        """Test that cycle is not skipped when mode is not skip_cycles."""
        # Default mode is 'adaptive', not 'skip_cycles'
        low_atrs = [0.0003, 0.0004, 0.0003]
        
        for _ in range(5):
            self.detector.detect_volatility(low_atrs)
        
        skip_decision = self.detector.should_skip_cycle()
        
        self.assertFalse(skip_decision['skip'])
    
    def test_empty_atr_readings(self):
        """Test handling of empty ATR readings list."""
        result = self.detector.detect_volatility([])
        
        self.assertEqual(result['state'], 'UNKNOWN')
        self.assertEqual(result['avg_atr'], 0.0)
        self.assertEqual(result['readings_count'], 0)
    
    def test_invalid_atr_readings(self):
        """Test filtering of invalid ATR readings."""
        # Include some zero and negative values
        invalid_atrs = [0.0010, 0.0, -0.0005, 0.0012, 0.0011]
        
        result = self.detector.detect_volatility(invalid_atrs)
        
        # Should only count valid positive ATR values
        self.assertEqual(result['readings_count'], 3)
        self.assertGreater(result['avg_atr'], 0.0)
    
    def test_status_retrieval(self):
        """Test getting volatility detector status."""
        low_atrs = [0.0003, 0.0004, 0.0003]
        self.detector.detect_volatility(low_atrs)
        
        status = self.detector.get_status()
        
        self.assertIn('state', status)
        self.assertIn('avg_atr', status)
        self.assertIn('consecutive_low_cycles', status)
        self.assertEqual(status['state'], 'LOW')
    
    def test_reset_functionality(self):
        """Test resetting volatility detector state."""
        low_atrs = [0.0003, 0.0004, 0.0003]
        self.detector.detect_volatility(low_atrs)
        self.detector.detect_volatility(low_atrs)
        
        self.assertNotEqual(self.detector.current_volatility_state, 'UNKNOWN')
        self.assertGreater(self.detector.consecutive_low_volatility_cycles, 0)
        
        self.detector.reset()
        
        self.assertEqual(self.detector.current_volatility_state, 'UNKNOWN')
        self.assertEqual(self.detector.consecutive_low_volatility_cycles, 0)
        self.assertEqual(len(self.detector.atr_history), 0)


class TestAdaptiveThresholdWithVolatility(unittest.TestCase):
    """Test adaptive threshold manager with volatility detection integration."""
    
    def setUp(self):
        """Create test database and managers."""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db = TradeDatabase(db_path=self.temp_db.name)
        
        # Create volatility detector
        self.volatility_detector = VolatilityDetector(
            low_threshold=0.0005,
            normal_threshold=0.0015,
            adjustment_mode='adaptive'
        )
        
        # Create adaptive threshold manager with volatility detector
        self.adaptive_mgr = AdaptiveThresholdManager(
            base_threshold=0.80,
            db=self.db,
            min_threshold=0.50,
            max_threshold=0.95,
            adjustment_step=0.02,
            volatility_detector=self.volatility_detector
        )
    
    def tearDown(self):
        """Clean up test database."""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_threshold_adjustment_with_low_volatility(self):
        """Test that threshold adjusts more aggressively in low volatility."""
        # Set low volatility state
        low_atrs = [0.0003, 0.0004, 0.0003]
        self.volatility_detector.detect_volatility(low_atrs)
        self.volatility_detector.detect_volatility(low_atrs)
        
        initial_threshold = self.adaptive_mgr.current_threshold
        
        # Trigger no-signal adjustment
        for _ in range(5):
            self.adaptive_mgr.update_on_cycle(0)
        
        # Threshold should have been lowered
        self.assertLess(self.adaptive_mgr.current_threshold, initial_threshold)
    
    def test_threshold_adjustment_with_normal_volatility(self):
        """Test normal threshold adjustment in normal volatility."""
        # Set normal volatility state
        normal_atrs = [0.0010, 0.0011, 0.0010]
        self.volatility_detector.detect_volatility(normal_atrs)
        
        initial_threshold = self.adaptive_mgr.current_threshold
        
        # Trigger no-signal adjustment
        for _ in range(5):
            self.adaptive_mgr.update_on_cycle(0)
        
        # Threshold should have been lowered, but not as aggressively
        self.assertLess(self.adaptive_mgr.current_threshold, initial_threshold)


class TestDatabaseVolatilityTracking(unittest.TestCase):
    """Test database storage of volatility readings."""
    
    def setUp(self):
        """Create test database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db = TradeDatabase(db_path=self.temp_db.name)
    
    def tearDown(self):
        """Clean up test database."""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_store_volatility_reading(self):
        """Test storing volatility reading in database."""
        vol_data = {
            'avg_atr': 0.0008,
            'state': 'NORMAL',
            'confidence': 0.85,
            'readings_count': 8,
            'consecutive_low_cycles': 0,
            'adjustment_mode': 'adaptive',
            'threshold_adjusted': False,
            'stops_adjusted': False,
            'cycle_skipped': False
        }
        
        reading_id = self.db.store_volatility_reading(vol_data)
        
        self.assertIsNotNone(reading_id)
        self.assertGreater(reading_id, 0)
    
    def test_retrieve_volatility_readings(self):
        """Test retrieving recent volatility readings."""
        # Store multiple readings
        for i in range(5):
            vol_data = {
                'avg_atr': 0.0008 + i * 0.0001,
                'state': 'NORMAL',
                'confidence': 0.85,
                'readings_count': 8,
                'consecutive_low_cycles': 0,
                'adjustment_mode': 'adaptive',
                'threshold_adjusted': False,
                'stops_adjusted': False,
                'cycle_skipped': False
            }
            self.db.store_volatility_reading(vol_data)
        
        readings = self.db.get_recent_volatility_readings(limit=3)
        
        # Verify we got the right number of readings
        self.assertEqual(len(readings), 3)
        # Verify expected fields are present
        self.assertIn('avg_atr', readings[0])
        self.assertIn('volatility_state', readings[0])
        self.assertIn('confidence', readings[0])
        self.assertIn('adjustment_mode', readings[0])
        # Verify all readings have ATR values in expected range
        for reading in readings:
            self.assertGreaterEqual(reading['avg_atr'], 0.0008)
            self.assertLessEqual(reading['avg_atr'], 0.0012)


if __name__ == '__main__':
    unittest.main()
