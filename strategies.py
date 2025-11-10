import pandas as pd
import pandas_ta as ta
import numpy as np

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

def calculate_indicators(df, atr_period=14, volume_ma_period=20):
    """Calculate all technical indicators for advanced_scalp strategy."""
    if len(df) < max(26, atr_period, volume_ma_period):
        return None
    
    # Make a copy to avoid modifying original
    df = df.copy()
    
    # RSI
    df['rsi'] = ta.rsi(df['close'], length=14)
    
    # MACD
    macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
    df['macd'] = macd['MACD_12_26_9']
    df['macd_signal'] = macd['MACDs_12_26_9']
    df['macd_hist'] = macd['MACDh_12_26_9']
    
    # Bollinger Bands
    bbands = ta.bbands(df['close'], length=20, std=2)
    # pandas_ta returns columns with format BBU_20_2.0_2.0 (length_std_mamode)
    bb_cols = [col for col in bbands.columns if col.startswith('BBL_')]
    if bb_cols:
        df['bb_lower'] = bbands[bb_cols[0]]
    bb_cols = [col for col in bbands.columns if col.startswith('BBM_')]
    if bb_cols:
        df['bb_middle'] = bbands[bb_cols[0]]
    bb_cols = [col for col in bbands.columns if col.startswith('BBU_')]
    if bb_cols:
        df['bb_upper'] = bbands[bb_cols[0]]
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
    
    # ATR for volatility
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=atr_period)
    
    # Volume analysis
    df['volume_ma'] = df['volume'].rolling(volume_ma_period).mean()
    df['volume_ratio'] = df['volume'] / df['volume_ma']
    
    return df

def advanced_scalp(df, atr_period=14, volume_ma_period=20, min_volume_ratio=1.2):
    """
    Advanced scalping strategy combining MACD, RSI, Bollinger Bands, ATR, and volume.
    Returns: (signal, confidence, atr_value) or (None, 0.0, 0.0)
    """
    df_indicators = calculate_indicators(df, atr_period, volume_ma_period)
    
    if df_indicators is None:
        return None, 0.0, 0.0
    
    latest = df_indicators.iloc[-1]
    prev = df_indicators.iloc[-2]
    
    # Check if we have valid data
    if pd.isna(latest['rsi']) or pd.isna(latest['macd']) or pd.isna(latest['atr']):
        return None, 0.0, 0.0
    
    signal = None
    confidence = 0.0
    
    # Signal components
    rsi_oversold = latest['rsi'] < 30
    rsi_overbought = latest['rsi'] > 70
    
    # MACD crossover
    macd_bullish_cross = prev['macd'] < prev['macd_signal'] and latest['macd'] > latest['macd_signal']
    macd_bearish_cross = prev['macd'] > prev['macd_signal'] and latest['macd'] < latest['macd_signal']
    
    # Bollinger squeeze (low volatility, potential breakout)
    bb_squeeze = latest['bb_width'] < df_indicators['bb_width'].rolling(20).mean().iloc[-1]
    
    # Price near Bollinger bands
    price_near_lower = latest['close'] < latest['bb_lower'] * 1.01
    price_near_upper = latest['close'] > latest['bb_upper'] * 0.99
    
    # Volume confirmation
    volume_confirmed = latest['volume_ratio'] > min_volume_ratio
    
    # BUY signal evaluation
    if (rsi_oversold or price_near_lower) and macd_bullish_cross:
        signal = 'BUY'
        confidence_factors = []
        
        # Base confidence from RSI oversold
        if rsi_oversold:
            confidence_factors.append(0.3)
        elif price_near_lower:
            confidence_factors.append(0.2)
        
        # MACD crossover confirmation
        confidence_factors.append(0.3)
        
        # Bollinger squeeze bonus
        if bb_squeeze:
            confidence_factors.append(0.1)
        
        # Volume confirmation
        if volume_confirmed:
            confidence_factors.append(0.2)
        
        # MACD histogram growing
        if latest['macd_hist'] > prev['macd_hist']:
            confidence_factors.append(0.1)
        
        confidence = min(sum(confidence_factors), 1.0)
    
    # SELL signal evaluation
    elif (rsi_overbought or price_near_upper) and macd_bearish_cross:
        signal = 'SELL'
        confidence_factors = []
        
        # Base confidence from RSI overbought
        if rsi_overbought:
            confidence_factors.append(0.3)
        elif price_near_upper:
            confidence_factors.append(0.2)
        
        # MACD crossover confirmation
        confidence_factors.append(0.3)
        
        # Bollinger squeeze bonus
        if bb_squeeze:
            confidence_factors.append(0.1)
        
        # Volume confirmation
        if volume_confirmed:
            confidence_factors.append(0.2)
        
        # MACD histogram declining
        if latest['macd_hist'] < prev['macd_hist']:
            confidence_factors.append(0.1)
        
        confidence = min(sum(confidence_factors), 1.0)
    
    return signal, confidence, latest['atr']

def get_signal(df, strategy):
    if strategy == 'scalping_rsi':
        return scalping_rsi(df)
    elif strategy == 'ma_crossover':
        return ma_crossover(df)
    elif strategy == 'advanced_scalp':
        signal, confidence, atr = advanced_scalp(df)
        # Return signal only if confidence is high enough
        # The bot will handle confidence threshold checking
        return signal
    # Add more strategies here
    return None

def get_signal_with_confidence(df, strategy, **kwargs):
    """Get signal with confidence score and ATR for advanced strategies."""
    if strategy == 'advanced_scalp':
        return advanced_scalp(df, **kwargs)
    else:
        # For backward compatibility, return signal with default confidence
        signal = get_signal(df, strategy)
        return signal, 1.0 if signal else 0.0, 0.0