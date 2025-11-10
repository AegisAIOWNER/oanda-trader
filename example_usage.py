#!/usr/bin/env python3
"""
Example usage of the advanced scalping strategy.

This script demonstrates how to:
1. Test the strategy with sample data
2. Evaluate signals and confidence scores
3. Calculate ATR-based stops
"""

import pandas as pd
import numpy as np
from strategies import advanced_scalp, get_signal_with_confidence, calculate_indicators
from config import CONFIDENCE_THRESHOLD, ATR_STOP_MULTIPLIER, ATR_PROFIT_MULTIPLIER

def create_sample_data(n=50, trend='neutral'):
    """Create sample OHLCV data for testing."""
    np.random.seed(42)
    base_price = 1.1000
    
    if trend == 'up':
        prices = base_price + np.arange(n) * 0.0002 + np.random.randn(n) * 0.0001
    elif trend == 'down':
        prices = base_price - np.arange(n) * 0.0002 + np.random.randn(n) * 0.0001
    else:
        prices = base_price + np.cumsum(np.random.randn(n) * 0.0001)
    
    df = pd.DataFrame({
        'open': prices + np.random.randn(n) * 0.00005,
        'high': prices + abs(np.random.randn(n) * 0.0001),
        'low': prices - abs(np.random.randn(n) * 0.0001),
        'close': prices,
        'volume': np.random.randint(100, 1000, n)
    })
    
    return df

def demonstrate_strategy():
    """Demonstrate the advanced scalping strategy."""
    print("=" * 70)
    print("ADVANCED SCALPING STRATEGY DEMONSTRATION")
    print("=" * 70)
    
    # Test with different market conditions
    conditions = ['neutral', 'up', 'down']
    
    for condition in conditions:
        print(f"\n{'─' * 70}")
        print(f"Market Condition: {condition.upper()}")
        print('─' * 70)
        
        # Create sample data
        df = create_sample_data(n=50, trend=condition)
        
        # Calculate indicators
        df_indicators = calculate_indicators(df)
        
        if df_indicators is not None:
            latest = df_indicators.iloc[-1]
            
            print(f"\nCurrent Market Data:")
            print(f"  Price: {latest['close']:.5f}")
            print(f"  RSI: {latest['rsi']:.2f}")
            print(f"  MACD: {latest['macd']:.6f}")
            print(f"  MACD Signal: {latest['macd_signal']:.6f}")
            print(f"  Bollinger Upper: {latest['bb_upper']:.5f}")
            print(f"  Bollinger Lower: {latest['bb_lower']:.5f}")
            print(f"  ATR: {latest['atr']:.6f}")
            print(f"  Volume Ratio: {latest['volume_ratio']:.2f}x")
            
            # Get signal
            signal, confidence, atr = advanced_scalp(df)
            
            print(f"\nStrategy Output:")
            print(f"  Signal: {signal if signal else 'NO SIGNAL'}")
            print(f"  Confidence: {confidence:.2%}")
            print(f"  ATR: {atr:.6f}")
            
            if signal and confidence >= CONFIDENCE_THRESHOLD:
                # Calculate stops
                stop_loss = atr * ATR_STOP_MULTIPLIER
                take_profit = atr * ATR_PROFIT_MULTIPLIER
                
                print(f"\n  ✓ TRADE SIGNAL GENERATED!")
                print(f"  Entry: {latest['close']:.5f}")
                if signal == 'BUY':
                    print(f"  Stop Loss: {latest['close'] - stop_loss:.5f} ({stop_loss:.6f} pips)")
                    print(f"  Take Profit: {latest['close'] + take_profit:.5f} ({take_profit:.6f} pips)")
                else:
                    print(f"  Stop Loss: {latest['close'] + stop_loss:.5f} ({stop_loss:.6f} pips)")
                    print(f"  Take Profit: {latest['close'] - take_profit:.5f} ({take_profit:.6f} pips)")
                print(f"  Risk/Reward Ratio: 1:{ATR_PROFIT_MULTIPLIER/ATR_STOP_MULTIPLIER:.2f}")
            elif signal:
                print(f"\n  ✗ Signal rejected (confidence {confidence:.2%} < threshold {CONFIDENCE_THRESHOLD:.2%})")
            else:
                print(f"\n  ○ No signal in current market conditions")

def demonstrate_confidence_scoring():
    """Demonstrate how confidence scoring works."""
    print("\n\n" + "=" * 70)
    print("CONFIDENCE SCORING BREAKDOWN")
    print("=" * 70)
    
    print("""
The confidence score (0.0 - 1.0) is calculated based on multiple factors:

1. BASE SIGNAL (0.3):
   - RSI oversold (< 30) for BUY
   - RSI overbought (> 70) for SELL
   - OR price near Bollinger Bands (0.2)

2. MACD CONFIRMATION (0.3):
   - Bullish crossover (MACD > Signal) for BUY
   - Bearish crossover (MACD < Signal) for SELL

3. VOLATILITY BONUS (0.1):
   - Bollinger Bands squeeze (low volatility, potential breakout)

4. VOLUME CONFIRMATION (0.2):
   - Current volume > 1.2× average volume

5. MOMENTUM BONUS (0.1):
   - MACD histogram increasing for BUY
   - MACD histogram decreasing for SELL

MINIMUM THRESHOLD: {threshold:.1%}
Only signals above this threshold are traded.

Example High-Quality Signal:
  RSI oversold (0.3) + MACD crossover (0.3) + Volume (0.2) + 
  Momentum (0.1) = 0.9 confidence → TRADE

Example Rejected Signal:
  Price near BB (0.2) + MACD crossover (0.3) = 0.5 confidence → NO TRADE
    """.format(threshold=CONFIDENCE_THRESHOLD))

if __name__ == '__main__':
    # Run demonstrations
    demonstrate_strategy()
    demonstrate_confidence_scoring()
    
    print("\n" + "=" * 70)
    print("To use this strategy in live trading:")
    print("  1. Configure your API keys in .env or config.py")
    print("  2. Set STRATEGY = 'advanced_scalp' in config.py")
    print("  3. Run: python cli.py start")
    print("=" * 70)
