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
        """Get performance metrics for position sizing."""
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
            return {'total_trades': 0, 'win_rate': 0.5, 'avg_win': 0.0, 'avg_loss': 0.0, 'sharpe': 0.0}
        
        pnls = [trade[0] for trade in trades if trade[0] is not None]
        if not pnls:
            return {'total_trades': 0, 'win_rate': 0.5, 'avg_win': 0.0, 'avg_loss': 0.0, 'sharpe': 0.0}
        
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        
        win_rate = len(wins) / len(pnls) if pnls else 0.5
        avg_win = sum(wins) / len(wins) if wins else 0.0
        avg_loss = sum(losses) / len(losses) if losses else 0.0
        
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
            'sharpe': sharpe
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
    
    def close(self):
        """Close method for compatibility with tests (no-op since we use connection per operation)."""
        pass
