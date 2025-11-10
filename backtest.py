import backtrader as bt
import pandas as pd
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

def backtest(instrument, data, strategy='ma_crossover'):
    """Run backtest for specified instrument and strategy."""
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
    cerebro.broker.setcash(10000.0)
    cerebro.broker.setcommission(commission=0.0001)
    
    # Run backtest
    print(f'Starting Portfolio Value: {cerebro.broker.getvalue():.2f}')
    cerebro.run()
    print(f'Final Portfolio Value: {cerebro.broker.getvalue():.2f}')
    
    return cerebro

# Example usage
if __name__ == '__main__':
    # Load historical data (implement data loading)
    df = pd.DataFrame()  # Replace with real data
    backtest('EUR_USD', df, strategy='advanced_scalp')