import pandas as pd
import pandas_ta as ta

def scalping_rsi(df):
    if len(df) < 14:
        return None
    rsi = ta.rsi(df['close'], length=14)
    if rsi.iloc[-1] < 30:
        return 'BUY'
    elif rsi.iloc[-1] > 70:
        return 'SELL'
    return None

def ma_crossover(df):
    if len(df) < 10:
        return None
    df['ma_short'] = df['close'].rolling(5).mean()
    df['ma_long'] = df['close'].rolling(10).mean()
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    if prev['ma_short'] < prev['ma_long'] and latest['ma_short'] > latest['ma_long']:
        return 'BUY'
    elif prev['ma_short'] > prev['ma_long'] and latest['ma_short'] < latest['ma_long']:
        return 'SELL'
    return None

def get_signal(df, strategy):
    if strategy == 'scalping_rsi':
        return scalping_rsi(df)
    elif strategy == 'ma_crossover':
        return ma_crossover(df)
    # Add more strategies here
    return None