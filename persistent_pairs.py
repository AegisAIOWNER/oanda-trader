"""
Persistent pairs manager for maintaining a list of tradable pairs across cycles.
This module ensures pairs are qualified and re-evaluated periodically, removing
those that no longer meet criteria.
"""
import json
import os
import time
import logging
from datetime import datetime


class PersistentPairsManager:
    """
    Manages a persistent list of trading pairs across bot cycles.
    
    Features:
    - Maintains a list of qualified pairs in memory and on disk
    - Periodically re-qualifies pairs to ensure they still meet criteria
    - Removes pairs that no longer qualify
    - Adds new qualifying pairs dynamically
    """
    
    def __init__(self, storage_file='data/persistent_pairs.json', 
                 requalification_interval=300, max_pairs=25):
        """
        Initialize the persistent pairs manager.
        
        Args:
            storage_file: Path to JSON file for persistent storage
            requalification_interval: Seconds between qualification checks
            max_pairs: Maximum number of pairs to maintain
        """
        self.storage_file = storage_file
        self.requalification_interval = requalification_interval
        self.max_pairs = max_pairs
        
        # In-memory pair storage
        # Structure: {instrument: {'added': timestamp, 'last_check': timestamp, 'qualified': bool}}
        self.pairs = {}
        
        # Create data directory if it doesn't exist
        os.makedirs(os.path.dirname(storage_file) if os.path.dirname(storage_file) else '.', exist_ok=True)
        
        # Load existing pairs from disk
        self._load_from_disk()
        
        logging.info(f"PersistentPairsManager initialized with {len(self.pairs)} pairs")
    
    def _load_from_disk(self):
        """Load pairs from disk storage."""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)
                    self.pairs = data.get('pairs', {})
                logging.info(f"Loaded {len(self.pairs)} pairs from {self.storage_file}")
            except Exception as e:
                logging.error(f"Failed to load pairs from disk: {e}")
                self.pairs = {}
        else:
            logging.info(f"No existing pairs file found at {self.storage_file}")
            self.pairs = {}
    
    def _save_to_disk(self):
        """Save pairs to disk storage."""
        try:
            data = {
                'pairs': self.pairs,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.storage_file, 'w') as f:
                json.dump(data, f, indent=2)
            logging.debug(f"Saved {len(self.pairs)} pairs to {self.storage_file}")
        except Exception as e:
            logging.error(f"Failed to save pairs to disk: {e}")
    
    def get_pairs_to_scan(self):
        """
        Get list of qualified pairs to scan for signals.
        
        Returns:
            list: List of instrument names that are currently qualified
        """
        # Filter only qualified pairs
        qualified = [
            instrument for instrument, info in self.pairs.items()
            if info.get('qualified', True)
        ]
        return qualified[:self.max_pairs]
    
    def add_pair(self, instrument):
        """
        Add a new pair to the persistent list.
        
        Args:
            instrument: Instrument name (e.g., 'EUR_USD')
        """
        if instrument not in self.pairs:
            self.pairs[instrument] = {
                'added': time.time(),
                'last_check': time.time(),
                'qualified': True
            }
            logging.info(f"Added new pair to persistent list: {instrument}")
            self._save_to_disk()
        else:
            # Re-qualify if it was previously disqualified
            if not self.pairs[instrument].get('qualified', True):
                self.pairs[instrument]['qualified'] = True
                self.pairs[instrument]['last_check'] = time.time()
                logging.info(f"Re-qualified pair: {instrument}")
                self._save_to_disk()
    
    def remove_pair(self, instrument):
        """
        Mark a pair as disqualified (not removed from list, just marked).
        
        Args:
            instrument: Instrument name to disqualify
        """
        if instrument in self.pairs:
            self.pairs[instrument]['qualified'] = False
            self.pairs[instrument]['last_check'] = time.time()
            logging.info(f"Disqualified pair: {instrument}")
            self._save_to_disk()
    
    def should_requalify_pairs(self):
        """
        Check if it's time to re-qualify pairs based on interval.
        
        Returns:
            bool: True if pairs should be re-qualified
        """
        if not self.pairs:
            return True  # Always qualify if empty
        
        # Check the oldest last_check time
        oldest_check = min(
            info.get('last_check', 0) for info in self.pairs.values()
        )
        
        return time.time() - oldest_check >= self.requalification_interval
    
    def update_pair_qualification(self, instrument, qualified):
        """
        Update the qualification status of a pair after checking.
        
        Args:
            instrument: Instrument name
            qualified: Boolean indicating if pair still qualifies
        """
        if instrument in self.pairs:
            self.pairs[instrument]['qualified'] = qualified
            self.pairs[instrument]['last_check'] = time.time()
            
            if not qualified:
                logging.info(f"Pair no longer qualifies: {instrument}")
            
            self._save_to_disk()
    
    def initialize_from_available(self, available_instruments):
        """
        Initialize persistent pairs from a list of available instruments.
        Only called if pairs list is empty.
        
        Args:
            available_instruments: List of available instrument names
        """
        if not self.pairs and available_instruments:
            # Add first N instruments
            for instrument in available_instruments[:self.max_pairs]:
                self.add_pair(instrument)
            logging.info(f"Initialized persistent pairs with {len(self.pairs)} instruments")
    
    def check_pair_qualification(self, instrument, data_df, strategy_func):
        """
        Check if a pair qualifies based on data availability and basic criteria.
        
        Args:
            instrument: Instrument name
            data_df: DataFrame with price data
            strategy_func: Function to check if pair generates any signals
            
        Returns:
            bool: True if pair qualifies, False otherwise
        """
        # Basic qualification checks:
        # 1. Must have sufficient data
        if data_df is None or data_df.empty or len(data_df) < 30:
            logging.debug(f"Pair {instrument} disqualified: insufficient data")
            return False
        
        # 2. Must have valid price data (no NaN, no zero prices)
        if data_df[['open', 'high', 'low', 'close']].isnull().any().any():
            logging.debug(f"Pair {instrument} disqualified: invalid price data")
            return False
        
        if (data_df[['open', 'high', 'low', 'close']] <= 0).any().any():
            logging.debug(f"Pair {instrument} disqualified: zero or negative prices")
            return False
        
        # 3. Must have some trading activity (volume > 0)
        if data_df['volume'].sum() == 0:
            logging.debug(f"Pair {instrument} disqualified: no trading volume")
            return False
        
        # All checks passed
        return True
    
    def get_stats(self):
        """
        Get statistics about the persistent pairs.
        
        Returns:
            dict: Statistics including total pairs, qualified pairs, etc.
        """
        qualified_count = sum(1 for info in self.pairs.values() if info.get('qualified', True))
        
        return {
            'total_pairs': len(self.pairs),
            'qualified_pairs': qualified_count,
            'disqualified_pairs': len(self.pairs) - qualified_count,
            'max_pairs': self.max_pairs
        }
    
    def __len__(self):
        """Return number of qualified pairs."""
        return len([p for p in self.pairs.values() if p.get('qualified', True)])
