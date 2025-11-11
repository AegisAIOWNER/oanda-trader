"""
Enhanced risk management system for trading bot.
Tracks positions, exposure, and enforces risk limits.
"""
import logging
from datetime import datetime
from collections import defaultdict


class RiskManager:
    """
    Manages risk across all trading operations.
    Tracks open positions, exposure, and enforces limits.
    """
    
    def __init__(self, max_open_positions=3, max_risk_per_trade=0.02,
                 max_total_risk=0.10, max_correlation_positions=2,
                 max_units_per_instrument=100000):
        """
        Initialize risk manager.
        
        Args:
            max_open_positions: Maximum concurrent positions
            max_risk_per_trade: Maximum risk per trade as fraction of balance
            max_total_risk: Maximum total risk as fraction of balance
            max_correlation_positions: Maximum positions in correlated instruments
            max_units_per_instrument: Maximum units per instrument
        """
        self.max_open_positions = max_open_positions
        self.max_risk_per_trade = max_risk_per_trade
        self.max_total_risk = max_total_risk
        self.max_correlation_positions = max_correlation_positions
        self.max_units_per_instrument = max_units_per_instrument
        
        # Track current state
        self.open_positions = {}  # instrument -> position details
        self.position_count = 0
        self.total_risk_amount = 0.0
        
        # Correlation groups (simplified - same base currency)
        self.correlation_groups = defaultdict(list)
        
        logging.info(f"RiskManager initialized: max_positions={max_open_positions}, "
                    f"max_risk_per_trade={max_risk_per_trade*100:.1f}%, "
                    f"max_total_risk={max_total_risk*100:.1f}%")
    
    def update_positions_from_api(self, api_positions):
        """
        Update internal state from API positions response.
        
        Args:
            api_positions: List of position dictionaries from API
        """
        self.open_positions = {}
        self.position_count = 0
        self.total_risk_amount = 0.0
        self.correlation_groups = defaultdict(list)
        
        for pos in api_positions:
            instrument = pos.get('instrument')
            if not instrument:
                continue
            
            long_units = float(pos.get('long', {}).get('units', 0))
            short_units = float(pos.get('short', {}).get('units', 0))
            
            # Calculate net position
            net_units = long_units + short_units  # short_units is negative
            
            if net_units != 0:
                self.open_positions[instrument] = {
                    'units': net_units,
                    'unrealized_pl': float(pos.get('unrealizedPL', 0)),
                    'long_units': long_units,
                    'short_units': abs(short_units)
                }
                self.position_count += 1
                
                # Track correlation groups
                base_currency = instrument.split('_')[0]
                self.correlation_groups[base_currency].append(instrument)
        
        logging.debug(f"Updated positions: {self.position_count} open, "
                     f"instruments: {list(self.open_positions.keys())}")
    
    def can_open_position(self, instrument, units, risk_amount, balance):
        """
        Check if a new position can be opened within risk limits.
        
        Args:
            instrument: Trading instrument
            units: Number of units to trade
            risk_amount: Risk amount in account currency
            balance: Current account balance
            
        Returns:
            tuple: (can_open, reason)
        """
        # Check max positions limit
        if self.position_count >= self.max_open_positions:
            return False, f"Maximum open positions reached: {self.position_count}/{self.max_open_positions}"
        
        # Check if position already exists
        if instrument in self.open_positions:
            return False, f"Position already open in {instrument}"
        
        # Check max units per instrument
        if abs(units) > self.max_units_per_instrument:
            return False, f"Units {abs(units)} exceeds maximum {self.max_units_per_instrument} for {instrument}"
        
        # Check risk per trade limit
        if balance > 0:
            risk_pct = risk_amount / balance
            if risk_pct > self.max_risk_per_trade:
                return False, f"Risk per trade ({risk_pct*100:.2f}%) exceeds maximum ({self.max_risk_per_trade*100:.2f}%)"
        
        # Check total risk limit
        if balance > 0:
            new_total_risk = (self.total_risk_amount + risk_amount) / balance
            if new_total_risk > self.max_total_risk:
                return False, f"Total risk ({new_total_risk*100:.2f}%) would exceed maximum ({self.max_total_risk*100:.2f}%)"
        
        # Check correlation limit (simplified - same base currency)
        base_currency = instrument.split('_')[0]
        correlated_count = len(self.correlation_groups.get(base_currency, []))
        if correlated_count >= self.max_correlation_positions:
            return False, f"Too many positions with {base_currency}: {correlated_count}/{self.max_correlation_positions}"
        
        return True, "OK to open position"
    
    def register_position(self, instrument, units, risk_amount):
        """
        Register a newly opened position.
        
        Args:
            instrument: Trading instrument
            units: Number of units
            risk_amount: Risk amount in account currency
        """
        if instrument in self.open_positions:
            logging.warning(f"Position in {instrument} already exists, updating")
        
        self.open_positions[instrument] = {
            'units': units,
            'risk_amount': risk_amount,
            'opened_at': datetime.now(),
            'unrealized_pl': 0.0
        }
        
        self.position_count = len(self.open_positions)
        self.total_risk_amount += risk_amount
        
        # Update correlation groups
        base_currency = instrument.split('_')[0]
        if instrument not in self.correlation_groups[base_currency]:
            self.correlation_groups[base_currency].append(instrument)
        
        logging.info(f"Registered position: {instrument}, units={units}, "
                    f"risk={risk_amount:.2f}, total_positions={self.position_count}")
    
    def close_position(self, instrument):
        """
        Remove a closed position from tracking.
        
        Args:
            instrument: Trading instrument
        """
        if instrument not in self.open_positions:
            logging.warning(f"Attempted to close non-existent position: {instrument}")
            return
        
        pos = self.open_positions[instrument]
        risk_amount = pos.get('risk_amount', 0.0)
        
        del self.open_positions[instrument]
        self.position_count = len(self.open_positions)
        self.total_risk_amount = max(0, self.total_risk_amount - risk_amount)
        
        # Update correlation groups
        base_currency = instrument.split('_')[0]
        if instrument in self.correlation_groups[base_currency]:
            self.correlation_groups[base_currency].remove(instrument)
        
        logging.info(f"Closed position: {instrument}, remaining_positions={self.position_count}")
    
    def get_position_info(self, instrument):
        """
        Get information about a specific position.
        
        Args:
            instrument: Trading instrument
            
        Returns:
            dict or None: Position information
        """
        return self.open_positions.get(instrument)
    
    def get_risk_summary(self, balance):
        """
        Get current risk exposure summary.
        
        Args:
            balance: Current account balance
            
        Returns:
            dict: Risk summary with percentages and limits
        """
        risk_pct = (self.total_risk_amount / balance * 100) if balance > 0 else 0.0
        
        return {
            'open_positions': self.position_count,
            'max_positions': self.max_open_positions,
            'positions_available': max(0, self.max_open_positions - self.position_count),
            'total_risk_amount': self.total_risk_amount,
            'total_risk_pct': risk_pct,
            'max_risk_pct': self.max_total_risk * 100,
            'risk_capacity_used_pct': (risk_pct / (self.max_total_risk * 100) * 100) if self.max_total_risk > 0 else 0,
            'instruments': list(self.open_positions.keys()),
            'correlation_groups': dict(self.correlation_groups)
        }
    
    def reset(self):
        """Reset risk manager state (for testing or manual intervention)."""
        self.open_positions = {}
        self.position_count = 0
        self.total_risk_amount = 0.0
        self.correlation_groups = defaultdict(list)
        logging.info("RiskManager state reset")


class OrderResponseHandler:
    """
    Handles and validates order responses, including partial fills.
    """
    
    @staticmethod
    def parse_order_response(response):
        """
        Parse order response and extract relevant information.
        
        Args:
            response: API order response
            
        Returns:
            dict: Parsed order information with status
        """
        if not response or not isinstance(response, dict):
            return {
                'success': False,
                'error': 'Invalid response format',
                'order_id': None,
                'fill_status': 'UNKNOWN'
            }
        
        # Check for errors
        if 'errorMessage' in response:
            return {
                'success': False,
                'error': response['errorMessage'],
                'order_id': None,
                'fill_status': 'ERROR'
            }
        
        # Extract order details
        order_create = response.get('orderCreateTransaction', {})
        order_fill = response.get('orderFillTransaction', {})
        order_cancel = response.get('orderCancelTransaction', {})
        
        # Determine fill status
        if order_fill:
            # Check for partial fill
            requested_units = abs(float(order_create.get('units', 0)))
            filled_units = abs(float(order_fill.get('units', 0)))
            
            if filled_units == 0:
                fill_status = 'NO_FILL'
            elif filled_units < requested_units:
                fill_status = 'PARTIAL_FILL'
            else:
                fill_status = 'FULL_FILL'
            
            return {
                'success': True,
                'order_id': order_fill.get('id'),
                'fill_status': fill_status,
                'requested_units': requested_units,
                'filled_units': filled_units,
                'fill_price': float(order_fill.get('price', 0)),
                'instrument': order_fill.get('instrument'),
                'time': order_fill.get('time'),
                'pl': float(order_fill.get('pl', 0)),
                'reason': order_fill.get('reason', 'MARKET_ORDER')
            }
        
        elif order_cancel:
            return {
                'success': False,
                'error': order_cancel.get('reason', 'Order cancelled'),
                'order_id': order_cancel.get('orderID'),
                'fill_status': 'CANCELLED',
                'reason': order_cancel.get('reason')
            }
        
        else:
            # Order created but not filled or cancelled (shouldn't happen with FOK)
            return {
                'success': False,
                'error': 'Order created but status unknown',
                'order_id': order_create.get('id'),
                'fill_status': 'PENDING'
            }
    
    @staticmethod
    def handle_partial_fill(order_info, expected_units, strategy='ACCEPT'):
        """
        Handle partial fill situations.
        
        Args:
            order_info: Parsed order information
            expected_units: Expected units to be filled
            strategy: How to handle partial fill ('ACCEPT', 'RETRY', 'CANCEL')
            
        Returns:
            dict: Action to take with reason
        """
        if order_info['fill_status'] != 'PARTIAL_FILL':
            return {'action': 'NONE', 'reason': 'Not a partial fill'}
        
        filled_pct = (order_info['filled_units'] / expected_units * 100) if expected_units > 0 else 0
        
        if strategy == 'ACCEPT':
            # Accept partial fill if at least 50% filled
            if filled_pct >= 50:
                return {
                    'action': 'ACCEPT',
                    'reason': f"Partial fill acceptable: {filled_pct:.1f}% filled",
                    'filled_units': order_info['filled_units']
                }
            else:
                return {
                    'action': 'CANCEL',
                    'reason': f"Partial fill too small: {filled_pct:.1f}% filled",
                    'filled_units': order_info['filled_units']
                }
        
        elif strategy == 'RETRY':
            # Try to fill remaining units
            remaining_units = expected_units - order_info['filled_units']
            return {
                'action': 'RETRY',
                'reason': f"Retrying for remaining units",
                'remaining_units': remaining_units
            }
        
        elif strategy == 'CANCEL':
            # Always cancel partial fills
            return {
                'action': 'CANCEL',
                'reason': 'Partial fills not accepted by strategy'
            }
        
        return {'action': 'ACCEPT', 'reason': 'Default action'}
