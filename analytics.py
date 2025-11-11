"""
Comprehensive P&L Analytics Module - Provides detailed trading performance analysis,
win rate tracking, drawdown monitoring, and actionable trading suggestions.
"""
import logging
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict


class AnalyticsEngine:
    """
    Comprehensive analytics engine for trading performance.
    Tracks P&L, win rates, drawdowns, and generates actionable insights.
    """
    
    def __init__(self, db, min_trades_for_suggestions=5, drawdown_threshold=0.10):
        """
        Initialize analytics engine.
        
        Args:
            db: TradeDatabase instance
            min_trades_for_suggestions: Minimum trades before generating suggestions
            drawdown_threshold: Alert threshold for drawdown (e.g., 0.10 = 10%)
        """
        self.db = db
        self.min_trades_for_suggestions = min_trades_for_suggestions
        self.drawdown_threshold = drawdown_threshold
        self.last_report_time = None
        
        logging.info(f"Analytics engine initialized: min_trades={min_trades_for_suggestions}, "
                     f"drawdown_threshold={drawdown_threshold:.1%}")
    
    def generate_comprehensive_report(self, days=30, current_balance=None):
        """
        Generate comprehensive analytics report.
        
        Args:
            days: Number of days to analyze
            current_balance: Current account balance (optional)
            
        Returns:
            dict: Comprehensive analytics data
        """
        import sqlite3
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        # Get all closed trades in the period
        cursor.execute('''
            SELECT 
                id, instrument, signal, confidence, entry_price, exit_price,
                stop_loss, take_profit, units, atr, ml_prediction, 
                position_size_pct, entry_time, exit_time, pnl, status
            FROM trades 
            WHERE status LIKE 'CLOSED%' 
            AND entry_time > datetime('now', '-{} days')
            ORDER BY entry_time ASC
        '''.format(days))
        
        trades = cursor.fetchall()
        conn.close()
        
        if not trades:
            return {
                'summary': {
                    'total_trades': 0,
                    'period_days': days,
                    'message': 'No completed trades in this period'
                }
            }
        
        # Parse trades
        trade_data = []
        for trade in trades:
            trade_data.append({
                'id': trade[0],
                'instrument': trade[1],
                'signal': trade[2],
                'confidence': trade[3],
                'entry_price': trade[4],
                'exit_price': trade[5],
                'stop_loss': trade[6],
                'take_profit': trade[7],
                'units': trade[8],
                'atr': trade[9],
                'ml_prediction': trade[10],
                'position_size_pct': trade[11],
                'entry_time': trade[12],
                'exit_time': trade[13],
                'pnl': trade[14],
                'status': trade[15]
            })
        
        # Calculate comprehensive metrics
        report = {
            'summary': self._calculate_summary_metrics(trade_data, days),
            'win_loss_analysis': self._analyze_win_loss(trade_data),
            'drawdown_analysis': self._analyze_drawdown(trade_data, current_balance),
            'instrument_performance': self._analyze_by_instrument(trade_data),
            'signal_performance': self._analyze_by_signal(trade_data),
            'confidence_analysis': self._analyze_by_confidence(trade_data),
            'ml_effectiveness': self._analyze_ml_effectiveness(trade_data),
            'time_analysis': self._analyze_by_time(trade_data),
            'suggestions': self._generate_suggestions(trade_data, current_balance)
        }
        
        self.last_report_time = datetime.now()
        return report
    
    def _calculate_summary_metrics(self, trade_data, days):
        """Calculate summary metrics."""
        if not trade_data:
            return {}
        
        pnls = [t['pnl'] for t in trade_data if t['pnl'] is not None]
        total_trades = len(pnls)
        
        if not pnls:
            return {'total_trades': 0}
        
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        breakevens = [p for p in pnls if p == 0]
        
        win_rate = len(wins) / total_trades if total_trades > 0 else 0
        avg_win = np.mean(wins) if wins else 0
        avg_loss = abs(np.mean(losses)) if losses else 0
        total_pnl = sum(pnls)
        
        # Profit factor
        total_wins = sum(wins) if wins else 0
        total_losses = abs(sum(losses)) if losses else 0.01  # Avoid division by zero
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Sharpe ratio (simplified)
        if len(pnls) > 1:
            returns_std = np.std(pnls)
            sharpe = (np.mean(pnls) / returns_std) * np.sqrt(252) if returns_std > 0 else 0
        else:
            sharpe = 0
        
        # Win/loss streak
        max_win_streak = self._calculate_max_streak(pnls, positive=True)
        max_loss_streak = self._calculate_max_streak(pnls, positive=False)
        
        return {
            'total_trades': total_trades,
            'period_days': days,
            'win_rate': win_rate,
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'breakeven_trades': len(breakevens),
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'total_pnl': total_pnl,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe,
            'max_win_streak': max_win_streak,
            'max_loss_streak': max_loss_streak,
            'risk_reward_ratio': avg_win / avg_loss if avg_loss > 0 else 0
        }
    
    def _analyze_win_loss(self, trade_data):
        """Analyze win/loss patterns."""
        if not trade_data:
            return {}
        
        wins = [t for t in trade_data if t['pnl'] and t['pnl'] > 0]
        losses = [t for t in trade_data if t['pnl'] and t['pnl'] < 0]
        
        return {
            'largest_win': max([t['pnl'] for t in wins]) if wins else 0,
            'largest_loss': min([t['pnl'] for t in losses]) if losses else 0,
            'avg_win_duration': self._avg_duration(wins) if wins else 0,
            'avg_loss_duration': self._avg_duration(losses) if losses else 0
        }
    
    def _analyze_drawdown(self, trade_data, current_balance):
        """Analyze drawdown metrics."""
        if not trade_data:
            return {}
        
        # Calculate cumulative P&L over time
        cumulative_pnl = []
        running_total = 0
        for trade in trade_data:
            if trade['pnl'] is not None:
                running_total += trade['pnl']
                cumulative_pnl.append(running_total)
        
        if not cumulative_pnl:
            return {'max_drawdown': 0, 'current_drawdown': 0}
        
        # Calculate maximum drawdown
        peak = cumulative_pnl[0]
        max_drawdown = 0
        
        for value in cumulative_pnl:
            if value > peak:
                peak = value
            drawdown = peak - value
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # Current drawdown (from peak to latest)
        current_drawdown = peak - cumulative_pnl[-1]
        
        # Calculate drawdown percentage if balance provided
        max_dd_pct = 0
        current_dd_pct = 0
        if current_balance and current_balance > 0:
            max_dd_pct = max_drawdown / current_balance
            current_dd_pct = current_drawdown / current_balance
        
        return {
            'max_drawdown': max_drawdown,
            'max_drawdown_pct': max_dd_pct,
            'current_drawdown': current_drawdown,
            'current_drawdown_pct': current_dd_pct,
            'alert': current_dd_pct > self.drawdown_threshold
        }
    
    def _analyze_by_instrument(self, trade_data):
        """Analyze performance by instrument."""
        instrument_stats = defaultdict(lambda: {'trades': [], 'pnl': []})
        
        for trade in trade_data:
            if trade['pnl'] is not None:
                instrument_stats[trade['instrument']]['trades'].append(trade)
                instrument_stats[trade['instrument']]['pnl'].append(trade['pnl'])
        
        results = {}
        for instrument, data in instrument_stats.items():
            pnls = data['pnl']
            wins = [p for p in pnls if p > 0]
            
            results[instrument] = {
                'total_trades': len(pnls),
                'win_rate': len(wins) / len(pnls) if pnls else 0,
                'total_pnl': sum(pnls),
                'avg_pnl': np.mean(pnls) if pnls else 0
            }
        
        return results
    
    def _analyze_by_signal(self, trade_data):
        """Analyze performance by signal type (BUY/SELL)."""
        signal_stats = defaultdict(lambda: {'pnl': []})
        
        for trade in trade_data:
            if trade['pnl'] is not None:
                signal_stats[trade['signal']]['pnl'].append(trade['pnl'])
        
        results = {}
        for signal, data in signal_stats.items():
            pnls = data['pnl']
            wins = [p for p in pnls if p > 0]
            
            results[signal] = {
                'total_trades': len(pnls),
                'win_rate': len(wins) / len(pnls) if pnls else 0,
                'total_pnl': sum(pnls),
                'avg_pnl': np.mean(pnls) if pnls else 0
            }
        
        return results
    
    def _analyze_by_confidence(self, trade_data):
        """Analyze performance by confidence levels."""
        # Group by confidence ranges
        ranges = {
            'low (0.5-0.7)': [],
            'medium (0.7-0.85)': [],
            'high (0.85-1.0)': []
        }
        
        for trade in trade_data:
            if trade['pnl'] is not None and trade['confidence']:
                conf = trade['confidence']
                if conf < 0.7:
                    ranges['low (0.5-0.7)'].append(trade['pnl'])
                elif conf < 0.85:
                    ranges['medium (0.7-0.85)'].append(trade['pnl'])
                else:
                    ranges['high (0.85-1.0)'].append(trade['pnl'])
        
        results = {}
        for range_name, pnls in ranges.items():
            if pnls:
                wins = [p for p in pnls if p > 0]
                results[range_name] = {
                    'total_trades': len(pnls),
                    'win_rate': len(wins) / len(pnls) if pnls else 0,
                    'avg_pnl': np.mean(pnls)
                }
        
        return results
    
    def _analyze_ml_effectiveness(self, trade_data):
        """Analyze ML prediction effectiveness."""
        ml_high = []  # ML prediction >= 0.7
        ml_low = []   # ML prediction < 0.5
        
        for trade in trade_data:
            if trade['pnl'] is not None and trade['ml_prediction']:
                ml_pred = trade['ml_prediction']
                if ml_pred >= 0.7:
                    ml_high.append(trade['pnl'])
                elif ml_pred < 0.5:
                    ml_low.append(trade['pnl'])
        
        results = {}
        if ml_high:
            wins_high = [p for p in ml_high if p > 0]
            results['high_ml_confidence'] = {
                'total_trades': len(ml_high),
                'win_rate': len(wins_high) / len(ml_high),
                'avg_pnl': np.mean(ml_high)
            }
        
        if ml_low:
            wins_low = [p for p in ml_low if p > 0]
            results['low_ml_confidence'] = {
                'total_trades': len(ml_low),
                'win_rate': len(wins_low) / len(ml_low),
                'avg_pnl': np.mean(ml_low)
            }
        
        return results
    
    def _analyze_by_time(self, trade_data):
        """Analyze performance by time of day."""
        time_stats = defaultdict(lambda: {'pnl': []})
        
        for trade in trade_data:
            if trade['pnl'] is not None and trade['entry_time']:
                try:
                    dt = datetime.fromisoformat(trade['entry_time'])
                    hour = dt.hour
                    
                    # Group into time periods
                    if 0 <= hour < 6:
                        period = 'night (00:00-06:00)'
                    elif 6 <= hour < 12:
                        period = 'morning (06:00-12:00)'
                    elif 12 <= hour < 18:
                        period = 'afternoon (12:00-18:00)'
                    else:
                        period = 'evening (18:00-00:00)'
                    
                    time_stats[period]['pnl'].append(trade['pnl'])
                except:
                    pass
        
        results = {}
        for period, data in time_stats.items():
            pnls = data['pnl']
            if pnls:
                wins = [p for p in pnls if p > 0]
                results[period] = {
                    'total_trades': len(pnls),
                    'win_rate': len(wins) / len(pnls),
                    'avg_pnl': np.mean(pnls)
                }
        
        return results
    
    def _generate_suggestions(self, trade_data, current_balance):
        """Generate actionable trading suggestions based on analysis."""
        if len(trade_data) < self.min_trades_for_suggestions:
            return ['Collect more trade data (minimum {} trades) for meaningful suggestions'.format(
                self.min_trades_for_suggestions)]
        
        suggestions = []
        
        # Analyze overall performance
        pnls = [t['pnl'] for t in trade_data if t['pnl'] is not None]
        if not pnls:
            return ['No P&L data available for analysis']
        
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        win_rate = len(wins) / len(pnls) if pnls else 0
        
        # Win rate suggestions
        if win_rate < 0.45:
            suggestions.append('⚠️ Low win rate ({:.1%}). Consider increasing confidence threshold or reviewing strategy parameters.'.format(win_rate))
        elif win_rate > 0.65:
            suggestions.append('✅ Strong win rate ({:.1%}). Current strategy is performing well!'.format(win_rate))
        
        # Risk/reward analysis
        avg_win = np.mean(wins) if wins else 0
        avg_loss = abs(np.mean(losses)) if losses else 0.01
        rr_ratio = avg_win / avg_loss if avg_loss > 0 else 0
        
        if rr_ratio < 1.5:
            suggestions.append('💡 Risk/reward ratio is {:.2f}. Consider widening take profit or tightening stop loss.'.format(rr_ratio))
        elif rr_ratio > 2.5:
            suggestions.append('✅ Excellent risk/reward ratio ({:.2f}). Well-optimized exits!'.format(rr_ratio))
        
        # Drawdown analysis
        dd_analysis = self._analyze_drawdown(trade_data, current_balance)
        if dd_analysis.get('alert'):
            suggestions.append('🚨 Current drawdown ({:.1%}) exceeds threshold. Consider reducing position sizes or pausing trading.'.format(
                dd_analysis['current_drawdown_pct']))
        
        # Instrument performance
        inst_perf = self._analyze_by_instrument(trade_data)
        if inst_perf:
            best_instrument = max(inst_perf.items(), key=lambda x: x[1]['total_pnl'])
            worst_instrument = min(inst_perf.items(), key=lambda x: x[1]['total_pnl'])
            
            if best_instrument[1]['total_pnl'] > 0:
                suggestions.append('📈 Best performing instrument: {} (P&L: {:.2f}, Win rate: {:.1%})'.format(
                    best_instrument[0], best_instrument[1]['total_pnl'], best_instrument[1]['win_rate']))
            
            if worst_instrument[1]['total_pnl'] < 0 and worst_instrument[1]['total_trades'] >= 3:
                suggestions.append('📉 Underperforming instrument: {} (P&L: {:.2f}, Win rate: {:.1%}). Consider removing from scan list.'.format(
                    worst_instrument[0], worst_instrument[1]['total_pnl'], worst_instrument[1]['win_rate']))
        
        # Signal direction bias
        signal_perf = self._analyze_by_signal(trade_data)
        if len(signal_perf) == 2:  # Both BUY and SELL
            buy_wr = signal_perf.get('BUY', {}).get('win_rate', 0)
            sell_wr = signal_perf.get('SELL', {}).get('win_rate', 0)
            
            if abs(buy_wr - sell_wr) > 0.20:
                better_signal = 'BUY' if buy_wr > sell_wr else 'SELL'
                suggestions.append('💡 {} signals performing significantly better ({:.1%} vs {:.1%}). Market may have directional bias.'.format(
                    better_signal, max(buy_wr, sell_wr), min(buy_wr, sell_wr)))
        
        # ML effectiveness
        ml_perf = self._analyze_ml_effectiveness(trade_data)
        if 'high_ml_confidence' in ml_perf and 'low_ml_confidence' in ml_perf:
            high_wr = ml_perf['high_ml_confidence']['win_rate']
            low_wr = ml_perf['low_ml_confidence']['win_rate']
            
            if high_wr > low_wr + 0.15:
                suggestions.append('🧠 ML predictions are effective! High ML confidence trades win {:.1%} vs {:.1%} for low confidence.'.format(
                    high_wr, low_wr))
        
        # Time-based patterns
        time_perf = self._analyze_by_time(trade_data)
        if time_perf:
            best_time = max(time_perf.items(), key=lambda x: x[1]['avg_pnl'])
            if best_time[1]['total_trades'] >= 3:
                suggestions.append('⏰ Best trading time: {} (Avg P&L: {:.2f}, Win rate: {:.1%})'.format(
                    best_time[0], best_time[1]['avg_pnl'], best_time[1]['win_rate']))
        
        if not suggestions:
            suggestions.append('✅ Trading performance is balanced. Continue monitoring metrics.')
        
        return suggestions
    
    def _calculate_max_streak(self, pnls, positive=True):
        """Calculate maximum winning or losing streak."""
        max_streak = 0
        current_streak = 0
        
        for pnl in pnls:
            if (positive and pnl > 0) or (not positive and pnl < 0):
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0
        
        return max_streak
    
    def _avg_duration(self, trades):
        """Calculate average trade duration in hours."""
        durations = []
        
        for trade in trades:
            if trade['entry_time'] and trade['exit_time']:
                try:
                    entry = datetime.fromisoformat(trade['entry_time'])
                    exit = datetime.fromisoformat(trade['exit_time'])
                    duration = (exit - entry).total_seconds() / 3600  # hours
                    durations.append(duration)
                except:
                    pass
        
        return np.mean(durations) if durations else 0
    
    def print_report(self, report):
        """Print formatted analytics report."""
        if not report:
            logging.info("No analytics data available")
            return
        
        logging.info("=" * 80)
        logging.info("📊 COMPREHENSIVE TRADING ANALYTICS REPORT")
        logging.info("=" * 80)
        
        # Summary
        if 'summary' in report:
            summary = report['summary']
            logging.info("\n📈 SUMMARY METRICS:")
            logging.info(f"  Period: {summary.get('period_days', 0)} days")
            logging.info(f"  Total Trades: {summary.get('total_trades', 0)}")
            logging.info(f"  Win Rate: {summary.get('win_rate', 0):.1%} "
                        f"({summary.get('winning_trades', 0)}W / {summary.get('losing_trades', 0)}L / {summary.get('breakeven_trades', 0)}BE)")
            logging.info(f"  Total P&L: {summary.get('total_pnl', 0):.2f}")
            logging.info(f"  Avg Win: {summary.get('avg_win', 0):.2f} | Avg Loss: {summary.get('avg_loss', 0):.2f}")
            logging.info(f"  Risk/Reward: {summary.get('risk_reward_ratio', 0):.2f}")
            logging.info(f"  Profit Factor: {summary.get('profit_factor', 0):.2f}")
            logging.info(f"  Sharpe Ratio: {summary.get('sharpe_ratio', 0):.2f}")
            logging.info(f"  Max Win Streak: {summary.get('max_win_streak', 0)} | Max Loss Streak: {summary.get('max_loss_streak', 0)}")
        
        # Drawdown
        if 'drawdown_analysis' in report:
            dd = report['drawdown_analysis']
            logging.info("\n📉 DRAWDOWN ANALYSIS:")
            logging.info(f"  Max Drawdown: {dd.get('max_drawdown', 0):.2f} ({dd.get('max_drawdown_pct', 0):.1%})")
            logging.info(f"  Current Drawdown: {dd.get('current_drawdown', 0):.2f} ({dd.get('current_drawdown_pct', 0):.1%})")
            if dd.get('alert'):
                logging.warning("  ⚠️ ALERT: Current drawdown exceeds threshold!")
        
        # Top instruments
        if 'instrument_performance' in report and report['instrument_performance']:
            logging.info("\n🎯 TOP INSTRUMENTS:")
            sorted_instruments = sorted(report['instrument_performance'].items(), 
                                      key=lambda x: x[1]['total_pnl'], reverse=True)
            for i, (inst, perf) in enumerate(sorted_instruments[:5], 1):
                logging.info(f"  {i}. {inst}: P&L {perf['total_pnl']:.2f}, Win rate {perf['win_rate']:.1%} ({perf['total_trades']} trades)")
        
        # Suggestions
        if 'suggestions' in report:
            logging.info("\n💡 ACTIONABLE SUGGESTIONS:")
            for suggestion in report['suggestions']:
                logging.info(f"  • {suggestion}")
        
        logging.info("=" * 80)
