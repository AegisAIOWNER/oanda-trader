"""
Trailing Stop Loss Manager - Dynamically adjusts stop losses as positions become profitable.
Moves stop loss by 50% of ATR as profit grows, protecting gains while allowing upside.
"""
import logging
from datetime import datetime


class TrailingStopManager:
    """
    Manages trailing stop losses for open positions.
    Moves stop loss up (for longs) or down (for shorts) by a fraction of ATR as profit grows.
    """
    
    def __init__(self, atr_multiplier=0.5, activation_multiplier=1.0):
        """
        Initialize trailing stop manager.
        
        Args:
            atr_multiplier: How much to move SL by (e.g., 0.5 = 50% of ATR)
            activation_multiplier: When to activate trailing (e.g., 1.0 = after 1x ATR profit)
        """
        self.atr_multiplier = atr_multiplier
        self.activation_multiplier = activation_multiplier
        self.position_trailing_state = {}  # Track trailing state per instrument
        
        logging.info(f"Trailing stop manager initialized: move_by={atr_multiplier:.1%} ATR, "
                     f"activate_at={activation_multiplier:.1f}x ATR profit")
    
    def should_activate_trailing(self, instrument, current_profit_pips, atr_pips):
        """
        Determine if trailing stop should be activated for a position.
        
        Args:
            instrument: Trading instrument
            current_profit_pips: Current profit in pips
            atr_pips: ATR value in pips for this position
            
        Returns:
            bool: True if trailing should be activated
        """
        if atr_pips <= 0:
            return False
        
        # Activate when profit >= activation_multiplier * ATR
        activation_threshold = self.activation_multiplier * atr_pips
        return current_profit_pips >= activation_threshold
    
    def calculate_new_stop_loss(self, instrument, direction, entry_price, current_price, 
                                 current_sl_price, atr_pips, pip_size):
        """
        Calculate new trailing stop loss price.
        
        Args:
            instrument: Trading instrument
            direction: 'BUY' or 'SELL'
            entry_price: Original entry price
            current_price: Current market price
            current_sl_price: Current stop loss price
            atr_pips: ATR value in pips
            pip_size: Pip size for the instrument (e.g., 0.0001 for EUR_USD)
            
        Returns:
            tuple: (new_sl_price, move_amount_pips, should_update)
        """
        # Calculate current profit in pips
        if direction == 'BUY':
            current_profit_pips = (current_price - entry_price) / pip_size
        else:  # SELL
            current_profit_pips = (entry_price - current_price) / pip_size
        
        # Check if we should activate trailing
        if not self.should_activate_trailing(instrument, current_profit_pips, atr_pips):
            return current_sl_price, 0.0, False
        
        # Calculate trailing move amount (50% of ATR by default)
        trailing_move_pips = self.atr_multiplier * atr_pips
        trailing_move_price = trailing_move_pips * pip_size
        
        # Get current trailing state for this instrument
        state = self.position_trailing_state.get(instrument, {
            'highest_price': current_price if direction == 'BUY' else None,
            'lowest_price': current_price if direction == 'SELL' else None,
            'last_sl_update': current_sl_price,
            'total_moves': 0
        })
        
        if direction == 'BUY':
            # For long positions, move SL up as price increases
            if state['highest_price'] is None or current_price > state['highest_price']:
                state['highest_price'] = current_price
                
                # Calculate new SL: move up by trailing_move_price from current SL
                new_sl_price = current_sl_price + trailing_move_price
                
                # Ensure new SL is not above current price (leave some room)
                max_sl_price = current_price - (trailing_move_price * 0.5)  # 50% buffer
                new_sl_price = min(new_sl_price, max_sl_price)
                
                # Only update if new SL is higher than current SL
                if new_sl_price > current_sl_price:
                    state['last_sl_update'] = new_sl_price
                    state['total_moves'] += 1
                    self.position_trailing_state[instrument] = state
                    
                    move_amount_pips = (new_sl_price - current_sl_price) / pip_size
                    logging.info(f"🔒 Trailing stop for {instrument}: Moving SL from {current_sl_price:.5f} "
                               f"to {new_sl_price:.5f} (+{move_amount_pips:.1f} pips)")
                    return new_sl_price, move_amount_pips, True
        
        else:  # SELL
            # For short positions, move SL down as price decreases
            if state['lowest_price'] is None or current_price < state['lowest_price']:
                state['lowest_price'] = current_price
                
                # Calculate new SL: move down by trailing_move_price from current SL
                new_sl_price = current_sl_price - trailing_move_price
                
                # Ensure new SL is not below current price (leave some room)
                min_sl_price = current_price + (trailing_move_price * 0.5)  # 50% buffer
                new_sl_price = max(new_sl_price, min_sl_price)
                
                # Only update if new SL is lower than current SL
                if new_sl_price < current_sl_price:
                    state['last_sl_update'] = new_sl_price
                    state['total_moves'] += 1
                    self.position_trailing_state[instrument] = state
                    
                    move_amount_pips = (current_sl_price - new_sl_price) / pip_size
                    logging.info(f"🔒 Trailing stop for {instrument}: Moving SL from {current_sl_price:.5f} "
                               f"to {new_sl_price:.5f} (-{move_amount_pips:.1f} pips)")
                    return new_sl_price, move_amount_pips, True
        
        # No update needed
        return current_sl_price, 0.0, False
    
    def get_trailing_stats(self, instrument):
        """
        Get trailing stop statistics for an instrument.
        
        Args:
            instrument: Trading instrument
            
        Returns:
            dict: Trailing statistics
        """
        state = self.position_trailing_state.get(instrument)
        if not state:
            return {
                'active': False,
                'total_moves': 0
            }
        
        return {
            'active': True,
            'total_moves': state.get('total_moves', 0),
            'highest_price': state.get('highest_price'),
            'lowest_price': state.get('lowest_price'),
            'last_sl_update': state.get('last_sl_update')
        }
    
    def clear_instrument_state(self, instrument):
        """
        Clear trailing state for an instrument (called when position closes).
        
        Args:
            instrument: Trading instrument
        """
        if instrument in self.position_trailing_state:
            del self.position_trailing_state[instrument]
            logging.debug(f"Cleared trailing state for {instrument}")
    
    def get_all_active_instruments(self):
        """
        Get list of all instruments with active trailing stops.
        
        Returns:
            list: List of instrument names
        """
        return list(self.position_trailing_state.keys())
