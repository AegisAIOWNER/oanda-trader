import backtrader as bt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from config import INSTRUMENTS, ATR_PERIOD, ATR_STOP_MULTIPLIER, ATR_PROFIT_MULTIPLIER, CONFIDENCE_THRESHOLD
from strategies import get_signal, get_signal_with_confidence, calculate_indicators

class MAStrategy(bt.Strategy):
    def __init__(self):
        self.ma_short = bt.indicators.SimpleMovingAverage(self.data.close, period=5)
        self.ma_long = bt.indicators.SimpleMovingAverage(self.data.close, period=10)

    def next(self):
        if not self.position:
            if self.ma_short > self.ma_long:
                self.buy()
        else:
            if self.ma_short < self.ma_long:
                self.sell()

class AdvancedScalpStrategy(bt.Strategy):
    """Backtrader strategy for advanced scalping with MACD, RSI, Bollinger Bands, and ATR."""
    
    params = (
        ('atr_period', ATR_PERIOD),
        ('atr_stop_mult', ATR_STOP_MULTIPLIER),
        ('atr_profit_mult', ATR_PROFIT_MULTIPLIER),
        ('confidence_threshold', CONFIDENCE_THRESHOLD),
    )
    
    def __init__(self):
        # Initialize indicators using backtrader
        self.rsi = bt.indicators.RSI(self.data.close, period=14)
        self.macd = bt.indicators.MACD(self.data.close, period_me1=12, period_me2=26, period_signal=9)
        self.bbands = bt.indicators.BollingerBands(self.data.close, period=20, devfactor=2)
        self.atr = bt.indicators.ATR(self.data, period=self.params.atr_period)
        
    def next(self):
        # Convert current data to DataFrame for strategy evaluation
        # Get last 50 bars for proper indicator calculation
        bars_needed = 50
        if len(self.data) < bars_needed:
            return
        
        # Build DataFrame from recent bars
        data_dict = {
            'open': [],
            'high': [],
            'low': [],
            'close': [],
            'volume': []
        }
        
        for i in range(-bars_needed, 0):
            data_dict['open'].append(self.data.open[i])
            data_dict['high'].append(self.data.high[i])
            data_dict['low'].append(self.data.low[i])
            data_dict['close'].append(self.data.close[i])
            data_dict['volume'].append(self.data.volume[i])
        
        df = pd.DataFrame(data_dict)
        
        # Get signal with confidence
        signal, confidence, atr = get_signal_with_confidence(df, 'advanced_scalp')
        
        if signal and confidence >= self.params.confidence_threshold:
            if signal == 'BUY' and not self.position:
                # Calculate position size and stops
                stop_distance = atr * self.params.atr_stop_mult if atr > 0 else 0.001
                profit_distance = atr * self.params.atr_profit_mult if atr > 0 else 0.002
                
                self.buy()
                self.sell(exectype=bt.Order.Stop, price=self.data.close[0] - stop_distance)
                self.sell(exectype=bt.Order.Limit, price=self.data.close[0] + profit_distance)
                
            elif signal == 'SELL' and not self.position:
                # Calculate position size and stops
                stop_distance = atr * self.params.atr_stop_mult if atr > 0 else 0.001
                profit_distance = atr * self.params.atr_profit_mult if atr > 0 else 0.002
                
                self.sell()
                self.buy(exectype=bt.Order.Stop, price=self.data.close[0] + stop_distance)
                self.buy(exectype=bt.Order.Limit, price=self.data.close[0] - profit_distance)

def calculate_sharpe_ratio(returns, risk_free_rate=0.02):
    """
    Calculate Sharpe ratio from returns.
    
    Args:
        returns: Series or array of returns
        risk_free_rate: Annual risk-free rate (default 2%)
        
    Returns:
        Sharpe ratio
    """
    if len(returns) == 0:
        return 0.0
    
    # Calculate excess returns
    excess_returns = returns - (risk_free_rate / 252)  # Daily risk-free rate
    
    # Calculate Sharpe ratio
    if excess_returns.std() == 0:
        return 0.0
    
    sharpe = excess_returns.mean() / excess_returns.std() * np.sqrt(252)  # Annualized
    return sharpe

def calculate_max_drawdown(equity_curve):
    """
    Calculate maximum drawdown from equity curve.
    
    Args:
        equity_curve: Array of portfolio values
        
    Returns:
        Maximum drawdown as percentage
    """
    if len(equity_curve) == 0:
        return 0.0
    
    cumulative = np.array(equity_curve)
    running_max = np.maximum.accumulate(cumulative)
    drawdown = (cumulative - running_max) / running_max
    max_dd = drawdown.min()
    
    return abs(max_dd)

def calculate_performance_metrics(cerebro, starting_value):
    """
    Calculate comprehensive performance metrics.
    
    Args:
        cerebro: Backtrader cerebro instance
        starting_value: Initial portfolio value
        
    Returns:
        Dictionary of performance metrics
    """
    final_value = cerebro.broker.getvalue()
    total_return = (final_value - starting_value) / starting_value
    
    # Extract trade information if available
    # Note: This is a simplified version - full implementation would track all trades
    
    metrics = {
        'starting_value': starting_value,
        'final_value': final_value,
        'total_return': total_return,
        'total_return_pct': total_return * 100,
        'profit': final_value - starting_value
    }
    
    return metrics

def backtest(instrument, data, strategy='ma_crossover', initial_cash=10000.0):
    """
    Run backtest for specified instrument and strategy with enhanced metrics.
    
    Args:
        instrument: Trading instrument
        data: DataFrame with OHLCV data
        strategy: Strategy name
        initial_cash: Starting portfolio value
        
    Returns:
        Dictionary with cerebro instance and metrics
    """
    cerebro = bt.Cerebro()
    
    # Select strategy
    if strategy == 'advanced_scalp':
        cerebro.addstrategy(AdvancedScalpStrategy)
    else:
        cerebro.addstrategy(MAStrategy)
    
    # Add data
    data_feed = bt.feeds.PandasData(dataname=data)
    cerebro.adddata(data_feed)
    
    # Set starting cash and commission
    cerebro.broker.setcash(initial_cash)
    cerebro.broker.setcommission(commission=0.0001)
    
    # Add analyzers for metrics
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', 
                       riskfreerate=0.02, annualize=True)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    # Run backtest
    starting_value = cerebro.broker.getvalue()
    print(f'Starting Portfolio Value: {starting_value:.2f}')
    
    results = cerebro.run()
    strat = results[0]
    
    final_value = cerebro.broker.getvalue()
    print(f'Final Portfolio Value: {final_value:.2f}')
    
    # Extract metrics from analyzers
    metrics = {
        'instrument': instrument,
        'strategy': strategy,
        'starting_value': starting_value,
        'final_value': final_value,
        'total_return': (final_value - starting_value) / starting_value,
        'total_return_pct': ((final_value - starting_value) / starting_value) * 100,
        'profit': final_value - starting_value
    }
    
    # Sharpe ratio
    sharpe_analysis = strat.analyzers.sharpe.get_analysis()
    sharpe_value = sharpe_analysis.get('sharperatio')
    metrics['sharpe_ratio'] = sharpe_value if sharpe_value is not None else 0.0
    
    # Drawdown
    drawdown_analysis = strat.analyzers.drawdown.get_analysis()
    metrics['max_drawdown'] = drawdown_analysis.get('max', {}).get('drawdown', 0.0)
    
    # Trade analysis
    trade_analysis = strat.analyzers.trades.get_analysis()
    total_trades = trade_analysis.get('total', {}).get('total', 0)
    won_trades = trade_analysis.get('won', {}).get('total', 0)
    lost_trades = trade_analysis.get('lost', {}).get('total', 0)
    
    metrics['total_trades'] = total_trades
    metrics['winning_trades'] = won_trades
    metrics['losing_trades'] = lost_trades
    metrics['win_rate'] = (won_trades / total_trades * 100) if total_trades > 0 else 0
    
    # Print comprehensive results
    print("\n" + "="*60)
    print(f"BACKTEST RESULTS - {instrument} ({strategy})")
    print("="*60)
    print(f"Total Return: {metrics['total_return_pct']:.2f}%")
    print(f"Profit/Loss: ${metrics['profit']:.2f}")
    print(f"Sharpe Ratio: {metrics['sharpe_ratio'] if metrics['sharpe_ratio'] else 'N/A'}")
    print(f"Max Drawdown: {metrics['max_drawdown']:.2f}%")
    print(f"Total Trades: {metrics['total_trades']}")
    print(f"Win Rate: {metrics['win_rate']:.2f}%")
    print("="*60 + "\n")
    
    return {
        'cerebro': cerebro,
        'metrics': metrics,
        'strategy_instance': strat
    }

def walk_forward_analysis(instrument, data, strategy='advanced_scalp',
                         train_period=252, test_period=63, initial_cash=10000.0):
    """
    Perform walk-forward analysis on the strategy.
    
    Walk-forward testing splits data into training and testing periods,
    optimizes on training data, and validates on testing data.
    
    Args:
        instrument: Trading instrument
        data: DataFrame with OHLCV data
        strategy: Strategy name
        train_period: Number of periods for training (e.g., 252 days = 1 year)
        test_period: Number of periods for testing (e.g., 63 days = 3 months)
        initial_cash: Starting portfolio value
        
    Returns:
        Dictionary with walk-forward results
    """
    logging.info(f"Starting walk-forward analysis for {instrument}")
    
    # Minimum data required for indicators (MACD needs 26 + 9 = 35 minimum)
    min_test_data = 50
    
    # Ensure test period is sufficient
    if test_period < min_test_data:
        logging.warning(f"Test period too small. Adjusting from {test_period} to {min_test_data}")
        test_period = min_test_data
    
    results = []
    total_periods = len(data)
    
    # Ensure we have enough data
    if total_periods < train_period + test_period:
        logging.warning(f"Insufficient data for walk-forward analysis. "
                       f"Need at least {train_period + test_period} periods, "
                       f"have {total_periods}")
        return None
    
    # Calculate number of walks
    num_walks = (total_periods - train_period) // test_period
    
    print(f"\n{'='*60}")
    print(f"WALK-FORWARD ANALYSIS - {instrument}")
    print(f"Train Period: {train_period} | Test Period: {test_period}")
    print(f"Number of Walks: {num_walks}")
    print(f"{'='*60}\n")
    
    for walk in range(num_walks):
        train_start = walk * test_period
        train_end = train_start + train_period
        test_start = train_end
        test_end = test_start + test_period
        
        if test_end > total_periods:
            break
        
        # Split data
        train_data = data.iloc[train_start:train_end].copy()
        test_data = data.iloc[test_start:test_end].copy()
        
        print(f"Walk {walk + 1}/{num_walks}:")
        print(f"  Training: rows {train_start} to {train_end}")
        print(f"  Testing:  rows {test_start} to {test_end}")
        
        # Run backtest on test period
        # Note: In a full implementation, we would optimize on train_data
        # and apply the optimized parameters to test_data
        test_result = backtest(instrument, test_data, strategy, initial_cash)
        
        walk_result = {
            'walk_number': walk + 1,
            'train_start': train_start,
            'train_end': train_end,
            'test_start': test_start,
            'test_end': test_end,
            'metrics': test_result['metrics']
        }
        
        results.append(walk_result)
    
    # Aggregate results
    if results:
        avg_return = np.mean([r['metrics']['total_return_pct'] for r in results])
        avg_sharpe = np.mean([r['metrics']['sharpe_ratio'] for r in results])
        avg_win_rate = np.mean([r['metrics']['win_rate'] for r in results])
        total_trades = sum([r['metrics']['total_trades'] for r in results])
        
        print(f"\n{'='*60}")
        print("WALK-FORWARD SUMMARY")
        print(f"{'='*60}")
        print(f"Average Return per Walk: {avg_return:.2f}%")
        print(f"Average Sharpe Ratio: {avg_sharpe:.4f}")
        print(f"Average Win Rate: {avg_win_rate:.2f}%")
        print(f"Total Trades Across All Walks: {total_trades}")
        print(f"{'='*60}\n")
        
        return {
            'walks': results,
            'summary': {
                'avg_return': avg_return,
                'avg_sharpe': avg_sharpe,
                'avg_win_rate': avg_win_rate,
                'total_trades': total_trades,
                'num_walks': len(results)
            }
        }
    
    return None

# Example usage
if __name__ == '__main__':
    # Load historical data (implement data loading)
    df = pd.DataFrame()  # Replace with real data
    backtest('EUR_USD', df, strategy='advanced_scalp')