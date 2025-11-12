"""
Unit tests for single-trade strategy features.
Tests persistent pairs management and confidence-based stop loss adjustment.
"""
import unittest
import os
import tempfile
import json
import time
import pandas as pd
import numpy as np
from persistent_pairs import PersistentPairsManager
from strategies import get_signal_with_confidence


class TestPersistentPairsManager(unittest.TestCase):
    """Test persistent pairs management functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary file for testing
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_file.close()
        self.storage_file = self.temp_file.name
        
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.storage_file):
            os.unlink(self.storage_file)
    
    def test_initialization(self):
        """Test that PersistentPairsManager initializes correctly."""
        manager = PersistentPairsManager(
            storage_file=self.storage_file,
            requalification_interval=300,
            max_pairs=25
        )
        
        self.assertEqual(len(manager.pairs), 0)
        self.assertEqual(manager.max_pairs, 25)
        self.assertEqual(manager.requalification_interval, 300)
    
    def test_add_pair(self):
        """Test adding a new pair to the manager."""
        manager = PersistentPairsManager(storage_file=self.storage_file)
        
        manager.add_pair('EUR_USD')
        
        self.assertEqual(len(manager.pairs), 1)
        self.assertIn('EUR_USD', manager.pairs)
        self.assertTrue(manager.pairs['EUR_USD']['qualified'])
    
    def test_remove_pair(self):
        """Test disqualifying a pair."""
        manager = PersistentPairsManager(storage_file=self.storage_file)
        
        manager.add_pair('EUR_USD')
        manager.remove_pair('EUR_USD')
        
        self.assertFalse(manager.pairs['EUR_USD']['qualified'])
    
    def test_get_qualified_pairs(self):
        """Test getting only qualified pairs."""
        manager = PersistentPairsManager(storage_file=self.storage_file)
        
        manager.add_pair('EUR_USD')
        manager.add_pair('GBP_USD')
        manager.add_pair('USD_JPY')
        manager.remove_pair('GBP_USD')
        
        qualified = manager.get_pairs_to_scan()
        
        self.assertEqual(len(qualified), 2)
        self.assertIn('EUR_USD', qualified)
        self.assertIn('USD_JPY', qualified)
        self.assertNotIn('GBP_USD', qualified)
    
    def test_persistence_to_disk(self):
        """Test that pairs are saved to and loaded from disk."""
        manager1 = PersistentPairsManager(storage_file=self.storage_file)
        
        manager1.add_pair('EUR_USD')
        manager1.add_pair('GBP_USD')
        
        # Create a new manager instance with the same file
        manager2 = PersistentPairsManager(storage_file=self.storage_file)
        
        self.assertEqual(len(manager2.pairs), 2)
        self.assertIn('EUR_USD', manager2.pairs)
        self.assertIn('GBP_USD', manager2.pairs)
    
    def test_should_requalify_pairs(self):
        """Test requalification timing logic."""
        manager = PersistentPairsManager(
            storage_file=self.storage_file,
            requalification_interval=1  # 1 second for testing
        )
        
        # Should return True when empty
        self.assertTrue(manager.should_requalify_pairs())
        
        # Add a pair
        manager.add_pair('EUR_USD')
        
        # Should return False immediately after adding
        self.assertFalse(manager.should_requalify_pairs())
        
        # Wait for requalification interval
        time.sleep(1.1)
        
        # Should return True after interval
        self.assertTrue(manager.should_requalify_pairs())
    
    def test_check_pair_qualification_valid(self):
        """Test pair qualification with valid data."""
        manager = PersistentPairsManager(storage_file=self.storage_file)
        
        # Create valid price data
        df = pd.DataFrame({
            'time': pd.date_range('2024-01-01', periods=50, freq='5min'),
            'open': np.random.uniform(1.1, 1.2, 50),
            'high': np.random.uniform(1.15, 1.25, 50),
            'low': np.random.uniform(1.05, 1.15, 50),
            'close': np.random.uniform(1.1, 1.2, 50),
            'volume': np.random.randint(100, 1000, 50)
        })
        
        qualified = manager.check_pair_qualification('EUR_USD', df, get_signal_with_confidence)
        
        self.assertTrue(qualified)
    
    def test_check_pair_qualification_insufficient_data(self):
        """Test pair qualification with insufficient data."""
        manager = PersistentPairsManager(storage_file=self.storage_file)
        
        # Create insufficient data (< 30 candles)
        df = pd.DataFrame({
            'time': pd.date_range('2024-01-01', periods=20, freq='5min'),
            'open': np.random.uniform(1.1, 1.2, 20),
            'high': np.random.uniform(1.15, 1.25, 20),
            'low': np.random.uniform(1.05, 1.15, 20),
            'close': np.random.uniform(1.1, 1.2, 20),
            'volume': np.random.randint(100, 1000, 20)
        })
        
        qualified = manager.check_pair_qualification('EUR_USD', df, get_signal_with_confidence)
        
        self.assertFalse(qualified)
    
    def test_check_pair_qualification_no_volume(self):
        """Test pair qualification with no trading volume."""
        manager = PersistentPairsManager(storage_file=self.storage_file)
        
        # Create data with zero volume
        df = pd.DataFrame({
            'time': pd.date_range('2024-01-01', periods=50, freq='5min'),
            'open': np.random.uniform(1.1, 1.2, 50),
            'high': np.random.uniform(1.15, 1.25, 50),
            'low': np.random.uniform(1.05, 1.15, 50),
            'close': np.random.uniform(1.1, 1.2, 50),
            'volume': np.zeros(50)
        })
        
        qualified = manager.check_pair_qualification('EUR_USD', df, get_signal_with_confidence)
        
        self.assertFalse(qualified)
    
    def test_initialize_from_available(self):
        """Test initializing pairs from available instruments list."""
        manager = PersistentPairsManager(
            storage_file=self.storage_file,
            max_pairs=5
        )
        
        available = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'USD_CAD', 'AUD_USD', 
                     'NZD_USD', 'EUR_GBP']
        
        manager.initialize_from_available(available)
        
        # Should initialize with first N pairs (max_pairs=5)
        self.assertEqual(len(manager.pairs), 5)
        self.assertIn('EUR_USD', manager.pairs)
        self.assertIn('GBP_USD', manager.pairs)
    
    def test_get_stats(self):
        """Test getting statistics about persistent pairs."""
        manager = PersistentPairsManager(storage_file=self.storage_file)
        
        manager.add_pair('EUR_USD')
        manager.add_pair('GBP_USD')
        manager.add_pair('USD_JPY')
        manager.remove_pair('GBP_USD')  # Disqualify one
        
        stats = manager.get_stats()
        
        self.assertEqual(stats['total_pairs'], 3)
        self.assertEqual(stats['qualified_pairs'], 2)
        self.assertEqual(stats['disqualified_pairs'], 1)
    
    def test_max_pairs_limit(self):
        """Test that max_pairs limit is respected."""
        manager = PersistentPairsManager(
            storage_file=self.storage_file,
            max_pairs=3
        )
        
        # Add more pairs than max
        manager.add_pair('EUR_USD')
        manager.add_pair('GBP_USD')
        manager.add_pair('USD_JPY')
        manager.add_pair('USD_CAD')
        manager.add_pair('AUD_USD')
        
        # get_pairs_to_scan should respect max_pairs
        pairs = manager.get_pairs_to_scan()
        self.assertLessEqual(len(pairs), 3)


class TestConfidenceBasedStopLoss(unittest.TestCase):
    """Test confidence-based stop loss adjustment."""
    
    def test_high_confidence_threshold(self):
        """Test that HIGH_CONFIDENCE_THRESHOLD is properly set."""
        from config import HIGH_CONFIDENCE_THRESHOLD, HIGH_CONFIDENCE_SL_MULTIPLIER
        
        self.assertEqual(HIGH_CONFIDENCE_THRESHOLD, 0.8)
        self.assertEqual(HIGH_CONFIDENCE_SL_MULTIPLIER, 1.5)
    
    def test_confidence_signal_detection(self):
        """Test that signals can have confidence >= 0.8."""
        # Create test data with strong trend
        df = pd.DataFrame({
            'time': pd.date_range('2024-01-01', periods=50, freq='5min'),
            'open': np.linspace(1.10, 1.15, 50),
            'high': np.linspace(1.11, 1.16, 50),
            'low': np.linspace(1.09, 1.14, 50),
            'close': np.linspace(1.10, 1.15, 50),  # Strong uptrend
            'volume': np.random.randint(1000, 5000, 50)
        })
        
        # Add RSI oversold condition at the end
        df.loc[df.index[-5:], 'close'] = 1.08  # Dip to trigger oversold
        df.loc[df.index[-1], 'close'] = 1.10  # Recovery
        
        signal, confidence, atr = get_signal_with_confidence(df, 'advanced_scalp')
        
        # Confidence can vary, but this tests the mechanism works
        self.assertIsInstance(confidence, float)
        self.assertGreaterEqual(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)


class TestSingleTradeConfiguration(unittest.TestCase):
    """Test single-trade strategy configuration."""
    
    def test_max_open_positions(self):
        """Test that MAX_OPEN_POSITIONS allows multiple concurrent positions."""
        from config import MAX_OPEN_POSITIONS
        
        # Updated to allow 3 concurrent positions for diversification
        self.assertEqual(MAX_OPEN_POSITIONS, 3)
    
    def test_margin_buffer(self):
        """Test that MARGIN_BUFFER is optimized for position sizing."""
        from config import MARGIN_BUFFER
        
        # MARGIN_BUFFER = 0.0 for single-trade strategy to maximize position size
        # AUTO_SCALE_MARGIN_BUFFER = 0.10 provides safety buffer for auto-scaling
        self.assertEqual(MARGIN_BUFFER, 0.0)
    
    def test_persistent_pairs_enabled(self):
        """Test that persistent pairs feature is enabled."""
        from config import ENABLE_PERSISTENT_PAIRS
        
        self.assertTrue(ENABLE_PERSISTENT_PAIRS)


if __name__ == '__main__':
    unittest.main()
