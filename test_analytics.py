"""
Tests for comprehensive analytics functionality.
"""
import unittest
import sqlite3
import os
from datetime import datetime, timedelta
from database import TradeDatabase
from analytics import AnalyticsEngine


class TestAnalyticsEngine(unittest.TestCase):
    """Test cases for AnalyticsEngine."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a unique temporary test database
        import time
        self.test_db_path = f'test_analytics_{int(time.time() * 1000)}.db'
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        
        self.db = TradeDatabase(db_path=self.test_db_path)
        self.analytics = AnalyticsEngine(
            db=self.db,
            min_trades_for_suggestions=3,
            drawdown_threshold=0.10
        )
        
        # Add some sample trades
        self._create_sample_trades()
    
    def tearDown(self):
        """Clean up test database."""
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
    
    def _create_sample_trades(self):
        """Create sample trades for testing."""
        base_time = datetime.now() - timedelta(days=15)
        
        trades = [
            # Winning trades
            {
                'instrument': 'EUR_USD',
                'signal': 'BUY',
                'confidence': 0.85,
                'entry_price': 1.1000,
                'stop_loss': 50,
                'take_profit': 100,
                'units': 1000,
                'atr': 0.001,
                'ml_prediction': 0.75,
                'position_size_pct': 0.02
            },
            {
                'instrument': 'GBP_USD',
                'signal': 'SELL',
                'confidence': 0.80,
                'entry_price': 1.3000,
                'stop_loss': 50,
                'take_profit': 100,
                'units': 1000,
                'atr': 0.001,
                'ml_prediction': 0.70,
                'position_size_pct': 0.02
            },
            # Losing trade
            {
                'instrument': 'USD_JPY',
                'signal': 'BUY',
                'confidence': 0.75,
                'entry_price': 110.00,
                'stop_loss': 50,
                'take_profit': 100,
                'units': 1000,
                'atr': 0.1,
                'ml_prediction': 0.60,
                'position_size_pct': 0.02
            },
        ]
        
        # Store and close trades with P&L - use same connection for all operations
        for i, trade in enumerate(trades):
            # Store trade
            conn = sqlite3.connect(self.test_db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO trades (
                    instrument, signal, confidence, entry_price, stop_loss, 
                    take_profit, units, atr, ml_prediction, position_size_pct
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade['instrument'],
                trade['signal'],
                trade['confidence'],
                trade['entry_price'],
                trade.get('stop_loss', 0.0),
                trade.get('take_profit', 0.0),
                trade['units'],
                trade.get('atr', 0.0),
                trade.get('ml_prediction', 0.5),
                trade.get('position_size_pct', 0.0)
            ))
            
            trade_id = cursor.lastrowid
            
            # Close the trade with P&L
            if i == 0:  # First trade wins
                pnl = 50.0
            elif i == 1:  # Second trade wins
                pnl = 45.0
            else:  # Third trade loses
                pnl = -30.0
            
            cursor.execute('''
                UPDATE trades 
                SET status = 'CLOSED', 
                    exit_price = entry_price + ?,
                    exit_time = ?,
                    pnl = ?
                WHERE id = ?
            ''', (0.001 if i < 2 else -0.001, datetime.now().isoformat(), pnl, trade_id))
            
            conn.commit()
            conn.close()
    
    def test_initialization(self):
        """Test analytics engine initialization."""
        self.assertEqual(self.analytics.min_trades_for_suggestions, 3)
        self.assertEqual(self.analytics.drawdown_threshold, 0.10)
    
    def test_generate_comprehensive_report(self):
        """Test generating a comprehensive report."""
        report = self.analytics.generate_comprehensive_report(days=30, current_balance=10000)
        
        # Check that report has all expected sections
        self.assertIn('summary', report)
        self.assertIn('win_loss_analysis', report)
        self.assertIn('drawdown_analysis', report)
        self.assertIn('instrument_performance', report)
        self.assertIn('signal_performance', report)
        self.assertIn('suggestions', report)
    
    def test_summary_metrics(self):
        """Test summary metrics calculation."""
        report = self.analytics.generate_comprehensive_report(days=30)
        summary = report['summary']
        
        self.assertEqual(summary['total_trades'], 3)
        self.assertEqual(summary['winning_trades'], 2)
        self.assertEqual(summary['losing_trades'], 1)
        self.assertAlmostEqual(summary['win_rate'], 2/3, places=2)
        self.assertEqual(summary['total_pnl'], 65.0)  # 50 + 45 - 30
    
    def test_win_loss_analysis(self):
        """Test win/loss analysis."""
        report = self.analytics.generate_comprehensive_report(days=30)
        wl_analysis = report['win_loss_analysis']
        
        self.assertEqual(wl_analysis['largest_win'], 50.0)
        self.assertEqual(wl_analysis['largest_loss'], -30.0)
    
    def test_drawdown_analysis(self):
        """Test drawdown analysis."""
        report = self.analytics.generate_comprehensive_report(days=30, current_balance=10000)
        dd_analysis = report['drawdown_analysis']
        
        self.assertIn('max_drawdown', dd_analysis)
        self.assertIn('current_drawdown', dd_analysis)
        self.assertIn('alert', dd_analysis)
        # With positive P&L, should not trigger alert
        self.assertFalse(dd_analysis['alert'])
    
    def test_instrument_performance(self):
        """Test performance by instrument."""
        report = self.analytics.generate_comprehensive_report(days=30)
        inst_perf = report['instrument_performance']
        
        self.assertIn('EUR_USD', inst_perf)
        self.assertIn('GBP_USD', inst_perf)
        self.assertIn('USD_JPY', inst_perf)
        
        # EUR_USD should have 1 trade with positive P&L
        eur_usd = inst_perf['EUR_USD']
        self.assertEqual(eur_usd['total_trades'], 1)
        self.assertEqual(eur_usd['win_rate'], 1.0)
        self.assertEqual(eur_usd['total_pnl'], 50.0)
    
    def test_signal_performance(self):
        """Test performance by signal type."""
        report = self.analytics.generate_comprehensive_report(days=30)
        signal_perf = report['signal_performance']
        
        self.assertIn('BUY', signal_perf)
        self.assertIn('SELL', signal_perf)
        
        # BUY has 2 trades (1 win, 1 loss)
        buy_perf = signal_perf['BUY']
        self.assertEqual(buy_perf['total_trades'], 2)
        self.assertEqual(buy_perf['win_rate'], 0.5)
        
        # SELL has 1 trade (1 win)
        sell_perf = signal_perf['SELL']
        self.assertEqual(sell_perf['total_trades'], 1)
        self.assertEqual(sell_perf['win_rate'], 1.0)
    
    def test_suggestions_generation(self):
        """Test that suggestions are generated."""
        report = self.analytics.generate_comprehensive_report(days=30, current_balance=10000)
        suggestions = report['suggestions']
        
        self.assertIsInstance(suggestions, list)
        self.assertGreater(len(suggestions), 0)
        
        # Should have at least one suggestion string
        self.assertTrue(all(isinstance(s, str) for s in suggestions))
    
    def test_insufficient_trades_for_suggestions(self):
        """Test behavior with insufficient trades."""
        # Create new engine with high threshold
        analytics = AnalyticsEngine(
            db=self.db,
            min_trades_for_suggestions=10,
            drawdown_threshold=0.10
        )
        
        report = analytics.generate_comprehensive_report(days=30)
        suggestions = report['suggestions']
        
        # Should have message about needing more trades
        self.assertGreater(len(suggestions), 0)
        self.assertIn('minimum', suggestions[0].lower())
    
    def test_print_report(self):
        """Test that print_report doesn't crash."""
        report = self.analytics.generate_comprehensive_report(days=30, current_balance=10000)
        
        # Should not raise any exceptions
        try:
            self.analytics.print_report(report)
            success = True
        except Exception as e:
            success = False
            print(f"Error printing report: {e}")
        
        self.assertTrue(success)
    
    def test_confidence_analysis(self):
        """Test confidence-based analysis."""
        report = self.analytics.generate_comprehensive_report(days=30)
        conf_analysis = report['confidence_analysis']
        
        # We have trades in medium and high confidence ranges
        self.assertGreater(len(conf_analysis), 0)
    
    def test_ml_effectiveness_analysis(self):
        """Test ML effectiveness analysis."""
        report = self.analytics.generate_comprehensive_report(days=30)
        ml_perf = report['ml_effectiveness']
        
        # Should have some ML data since we set ml_prediction in sample trades
        if ml_perf:  # May be empty if not enough data
            for key, data in ml_perf.items():
                self.assertIn('total_trades', data)
                self.assertIn('win_rate', data)


if __name__ == '__main__':
    unittest.main()
