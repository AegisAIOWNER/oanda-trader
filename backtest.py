import backtrader as bt
import pandas as pd
from config import INSTRUMENTS
from strategies import get_signal

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

def backtest(instrument, data):
    cerebro = bt.Cerebro()
    cerebro.addstrategy(MAStrategy)
    data_feed = bt.feeds.PandasData(dataname=data)
    cerebro.adddata(data_feed)
    cerebro.run()
    cerebro.plot()

# Example usage
if __name__ == '__main__':
    # Load historical data (implement data loading)
    df = pd.DataFrame()  # Replace with real data
    backtest('EUR_USD', df)