import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import logging

class TradeDatabase:
    """Database for storing trade history and performance metrics."""
    
    def __init__(self, db_path='trades.db'):
        self.db_path = db_path
        self._create_tables()
    
    def _create_tables(self):
        """Create necessary database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create trades table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instrument TEXT NOT NULL,
                signal TEXT NOT NULL,
                confidence REAL,
                entry_price REAL,
                stop_loss REAL,
                take_profit REAL,
                units INTEGER,
                atr REAL,
                ml_prediction REAL,
                position_size_pct REAL,
                entry_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                exit_price REAL,
                exit_time TIMESTAMP,
                pnl REAL,
                status TEXT DEFAULT 'OPEN'
            )
        ''')
        
        # Create threshold adjustments table for autonomous learning
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS threshold_adjustments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                old_threshold REAL NOT NULL,
                new_threshold REAL NOT NULL,
                adjustment_reason TEXT NOT NULL,
                cycles_without_signal INTEGER DEFAULT 0,
                recent_win_rate REAL,
                recent_profit_factor REAL,
                total_trades_analyzed INTEGER DEFAULT 0
            )
        ''')
        
        # Create volatility readings table for market condition tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS volatility_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                avg_atr REAL NOT NULL,
                volatility_state TEXT NOT NULL,
                confidence REAL,
                readings_count INTEGER,
                consecutive_low_cycles INTEGER DEFAULT 0,
                adjustment_mode TEXT,
                threshold_adjusted BOOLEAN DEFAULT 0,
                stops_adjusted BOOLEAN DEFAULT 0,
                cycle_skipped BOOLEAN DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def store_trade(self, trade_data):
        """Store a new trade in the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO trades (
                instrument, signal, confidence, entry_price, stop_loss, 
                take_profit, units, atr, ml_prediction, position_size_pct
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade_data['instrument'],
            trade_data['signal'],
            trade_data['confidence'],
            trade_data['entry_price'],
            trade_data.get('stop_loss', 0.0),
            trade_data.get('take_profit', 0.0),
            trade_data['units'],
            trade_data.get('atr', 0.0),
            trade_data.get('ml_prediction', 0.5),
            trade_data.get('position_size_pct', 0.0)
        ))
        
        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()
        logging.info(f"Trade stored in database: {trade_data['instrument']} {trade_data['signal']}")
        return trade_id
    
    def update_trade_exit(self, trade_id, exit_price, pnl):
        """Update trade with exit information."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE trades 
            SET exit_price = ?, exit_time = CURRENT_TIMESTAMP, pnl = ?, status = 'CLOSED'
            WHERE id = ?
        ''', (exit_price, pnl, trade_id))
        
        conn.commit()
        conn.close()
    
    def get_performance_metrics(self, days=30):
        """Get performance metrics for position sizing and adaptive threshold."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get recent trades
        cursor.execute('''
            SELECT pnl, entry_time FROM trades 
            WHERE status = 'CLOSED' AND entry_time > datetime('now', '-{} days')
            ORDER BY entry_time DESC
        '''.format(days))
        
        trades = cursor.fetchall()
        conn.close()
        
        if not trades:
            return {'total_trades': 0, 'win_rate': 0.5, 'avg_win': 0.0, 'avg_loss': 0.0, 
                    'sharpe': 0.0, 'profit_factor': 1.0}
        
        pnls = [trade[0] for trade in trades if trade[0] is not None]
        if not pnls:
            return {'total_trades': 0, 'win_rate': 0.5, 'avg_win': 0.0, 'avg_loss': 0.0, 
                    'sharpe': 0.0, 'profit_factor': 1.0}
        
        wins = [p for p in pnls if p > 0]
        losses = [abs(p) for p in pnls if p < 0]  # Absolute value for losses
        
        win_rate = len(wins) / len(pnls) if pnls else 0.5
        avg_win = sum(wins) / len(wins) if wins else 0.0
        avg_loss = sum(losses) / len(losses) if losses else 0.0
        
        # Calculate profit factor (total wins / total losses)
        total_wins = sum(wins) if wins else 0.0
        total_losses = sum(losses) if losses else 0.0
        profit_factor = total_wins / total_losses if total_losses > 0 else (2.0 if total_wins > 0 else 1.0)
        
        # Simple Sharpe ratio approximation
        if len(pnls) > 1:
            returns = pd.Series(pnls)
            sharpe = returns.mean() / returns.std() if returns.std() > 0 else 0.0
        else:
            sharpe = 0.0
        
        return {
            'total_trades': len(pnls),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'sharpe': sharpe,
            'profit_factor': profit_factor
        }
    
    def update_trade(self, trade_id, exit_price, pnl, status='closed'):
        """Update trade with exit information (alias for update_trade_exit)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE trades 
            SET exit_price = ?, exit_time = CURRENT_TIMESTAMP, pnl = ?, status = ?
            WHERE id = ?
        ''', (exit_price, pnl, status.upper(), trade_id))
        
        conn.commit()
        conn.close()
    
    def get_recent_trades(self, limit=10):
        """Get recent trades for analysis."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM trades ORDER BY entry_time DESC LIMIT ?
        ''', (limit,))
        
        columns = [desc[0] for desc in cursor.description]
        trades = cursor.fetchall()
        conn.close()
        
        return [dict(zip(columns, trade)) for trade in trades]
    
    def store_threshold_adjustment(self, adjustment_data):
        """Store a threshold adjustment decision for learning."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO threshold_adjustments (
                old_threshold, new_threshold, adjustment_reason,
                cycles_without_signal, recent_win_rate, recent_profit_factor,
                total_trades_analyzed
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            adjustment_data['old_threshold'],
            adjustment_data['new_threshold'],
            adjustment_data['adjustment_reason'],
            adjustment_data.get('cycles_without_signal', 0),
            adjustment_data.get('recent_win_rate', None),
            adjustment_data.get('recent_profit_factor', None),
            adjustment_data.get('total_trades_analyzed', 0)
        ))
        
        adjustment_id = cursor.lastrowid
        conn.commit()
        conn.close()
        logging.info(f"Threshold adjustment stored: {adjustment_data['old_threshold']:.3f} → "
                     f"{adjustment_data['new_threshold']:.3f} ({adjustment_data['adjustment_reason']})")
        return adjustment_id
    
    def get_recent_threshold_adjustments(self, limit=10):
        """Get recent threshold adjustments for analysis."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM threshold_adjustments 
            ORDER BY timestamp DESC LIMIT ?
        ''', (limit,))
        
        columns = [desc[0] for desc in cursor.description]
        adjustments = cursor.fetchall()
        conn.close()
        
        return [dict(zip(columns, adj)) for adj in adjustments]
    
    def get_last_threshold(self):
        """Get the last adjusted threshold value from the database.
        
        Returns:
            float: The last threshold value, or None if no adjustments exist
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT new_threshold FROM threshold_adjustments 
            ORDER BY id DESC LIMIT 1
        ''')
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def store_volatility_reading(self, volatility_data):
        """Store a volatility reading for market condition tracking."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO volatility_readings (
                avg_atr, volatility_state, confidence, readings_count,
                consecutive_low_cycles, adjustment_mode, threshold_adjusted,
                stops_adjusted, cycle_skipped
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            volatility_data['avg_atr'],
            volatility_data['state'],
            volatility_data.get('confidence', 0.0),
            volatility_data.get('readings_count', 0),
            volatility_data.get('consecutive_low_cycles', 0),
            volatility_data.get('adjustment_mode', 'none'),
            volatility_data.get('threshold_adjusted', False),
            volatility_data.get('stops_adjusted', False),
            volatility_data.get('cycle_skipped', False)
        ))
        
        reading_id = cursor.lastrowid
        conn.commit()
        conn.close()
        logging.info(f"Volatility reading stored: {volatility_data['state']} "
                     f"(avg_atr={volatility_data['avg_atr']:.6f})")
        return reading_id
    
    def get_recent_volatility_readings(self, limit=10):
        """Get recent volatility readings for analysis."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM volatility_readings 
            ORDER BY timestamp DESC LIMIT ?
        ''', (limit,))
        
        columns = [desc[0] for desc in cursor.description]
        readings = cursor.fetchall()
        conn.close()
        
        return [dict(zip(columns, reading)) for reading in readings]
    
    def close(self):
        """Close method for compatibility with tests (no-op since we use connection per operation)."""
        pass
