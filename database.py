"""
Database module for storing trade history and model training data.
"""
import sqlite3
import pandas as pd
from datetime import datetime
import logging
import json

class TradeDatabase:
    """SQLite database for storing trade history and analytics."""
    
    def __init__(self, db_path='trades.db'):
        self.db_path = db_path
        self.conn = None
        self._init_database()
    
    def _init_database(self):
        """Initialize database and create tables if they don't exist."""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cursor = self.conn.cursor()
        
        # Trade history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                instrument TEXT NOT NULL,
                signal TEXT NOT NULL,
                confidence REAL NOT NULL,
                entry_price REAL NOT NULL,
                stop_loss REAL,
                take_profit REAL,
                units INTEGER NOT NULL,
                atr REAL,
                exit_price REAL,
                exit_timestamp TEXT,
                profit_loss REAL,
                status TEXT DEFAULT 'open',
                ml_prediction REAL,
                position_size_pct REAL
            )
        ''')
        
        # Market data for model training
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                instrument TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume INTEGER NOT NULL,
                rsi REAL,
                macd REAL,
                macd_signal REAL,
                atr REAL,
                bb_upper REAL,
                bb_lower REAL,
                UNIQUE(timestamp, instrument, timeframe)
            )
        ''')
        
        # Model training history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS model_training (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                model_type TEXT NOT NULL,
                accuracy REAL,
                precision_score REAL,
                recall_score REAL,
                f1_score REAL,
                training_samples INTEGER,
                parameters TEXT
            )
        ''')
        
        self.conn.commit()
        logging.info(f"Database initialized at {self.db_path}")
    
    def store_trade(self, trade_data):
        """Store a new trade in the database."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO trades (
                timestamp, instrument, signal, confidence, entry_price,
                stop_loss, take_profit, units, atr, ml_prediction, position_size_pct
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade_data.get('timestamp', datetime.now().isoformat()),
            trade_data['instrument'],
            trade_data['signal'],
            trade_data['confidence'],
            trade_data['entry_price'],
            trade_data.get('stop_loss'),
            trade_data.get('take_profit'),
            trade_data['units'],
            trade_data.get('atr'),
            trade_data.get('ml_prediction'),
            trade_data.get('position_size_pct')
        ))
        self.conn.commit()
        return cursor.lastrowid
    
    def update_trade(self, trade_id, exit_price, profit_loss, status='closed'):
        """Update a trade with exit information."""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE trades
            SET exit_price = ?, exit_timestamp = ?, profit_loss = ?, status = ?
            WHERE id = ?
        ''', (exit_price, datetime.now().isoformat(), profit_loss, status, trade_id))
        self.conn.commit()
    
    def store_market_data(self, data_dict):
        """Store market data for model training."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO market_data (
                timestamp, instrument, timeframe, open, high, low, close, volume,
                rsi, macd, macd_signal, atr, bb_upper, bb_lower
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data_dict['timestamp'],
            data_dict['instrument'],
            data_dict['timeframe'],
            data_dict['open'],
            data_dict['high'],
            data_dict['low'],
            data_dict['close'],
            data_dict['volume'],
            data_dict.get('rsi'),
            data_dict.get('macd'),
            data_dict.get('macd_signal'),
            data_dict.get('atr'),
            data_dict.get('bb_upper'),
            data_dict.get('bb_lower')
        ))
        self.conn.commit()
    
    def store_model_training(self, training_data):
        """Store model training results."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO model_training (
                timestamp, model_type, accuracy, precision_score, recall_score,
                f1_score, training_samples, parameters
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            training_data['model_type'],
            training_data.get('accuracy'),
            training_data.get('precision'),
            training_data.get('recall'),
            training_data.get('f1'),
            training_data['training_samples'],
            json.dumps(training_data.get('parameters', {}))
        ))
        self.conn.commit()
    
    def get_training_data(self, instrument=None, min_samples=100):
        """Get historical data for model training."""
        query = '''
            SELECT timestamp, instrument, open, high, low, close, volume,
                   rsi, macd, macd_signal, atr, bb_upper, bb_lower
            FROM market_data
        '''
        params = []
        
        if instrument:
            query += ' WHERE instrument = ?'
            params.append(instrument)
        
        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(min_samples * 2)  # Get more data for feature engineering
        
        df = pd.read_sql_query(query, self.conn, params=params)
        return df
    
    def get_trade_history(self, limit=100):
        """Get recent trade history."""
        query = '''
            SELECT * FROM trades
            ORDER BY timestamp DESC
            LIMIT ?
        '''
        df = pd.read_sql_query(query, self.conn, params=[limit])
        return df
    
    def get_performance_metrics(self, days=30):
        """Calculate performance metrics from trade history."""
        query = '''
            SELECT * FROM trades
            WHERE status = 'closed'
            AND timestamp >= datetime('now', '-{} days')
            ORDER BY timestamp
        '''.format(days)
        
        df = pd.read_sql_query(query, self.conn)
        
        if len(df) == 0:
            return {}
        
        total_trades = len(df)
        winning_trades = len(df[df['profit_loss'] > 0])
        losing_trades = len(df[df['profit_loss'] < 0])
        
        metrics = {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': winning_trades / total_trades if total_trades > 0 else 0,
            'total_profit': df['profit_loss'].sum(),
            'average_profit': df[df['profit_loss'] > 0]['profit_loss'].mean() if winning_trades > 0 else 0,
            'average_loss': df[df['profit_loss'] < 0]['profit_loss'].mean() if losing_trades > 0 else 0,
            'largest_win': df['profit_loss'].max() if total_trades > 0 else 0,
            'largest_loss': df['profit_loss'].min() if total_trades > 0 else 0
        }
        
        return metrics
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logging.info("Database connection closed")
