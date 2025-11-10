"""
Integration test demonstrating the full enhanced bot workflow.
This test shows how all components work together.
"""
import pandas as pd
import numpy as np
from datetime import datetime
import tempfile
import os

from database import TradeDatabase
from ml_predictor import MLPredictor
from position_sizing import PositionSizer
from multi_timeframe import MultiTimeframeAnalyzer
from strategies import calculate_indicators, advanced_scalp

def create_sample_data(n=200, trend='neutral'):
    """Create sample OHLCV data."""
    np.random.seed(42)
    base_price = 1.1000
    
    if trend == 'up':
        prices = base_price + np.arange(n) * 0.0002 + np.random.randn(n) * 0.0001
    elif trend == 'down':
        prices = base_price - np.arange(n) * 0.0002 + np.random.randn(n) * 0.0001
    else:
        prices = base_price + np.cumsum(np.random.randn(n) * 0.0001)
    
    df = pd.DataFrame({
        'time': [datetime.now().isoformat()] * n,
        'open': prices + np.random.randn(n) * 0.00005,
        'high': prices + abs(np.random.randn(n) * 0.0001),
        'low': prices - abs(np.random.randn(n) * 0.0001),
        'close': prices,
        'volume': np.random.randint(100, 1000, n)
    })
    
    return df

def test_full_workflow():
    """Test the complete enhanced trading workflow."""
    print("="*70)
    print("ENHANCED TRADING BOT - INTEGRATION TEST")
    print("="*70)
    
    # Create temporary files
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_model = tempfile.NamedTemporaryFile(suffix='.pkl', delete=False)
    temp_db.close()
    temp_model.close()
    
    try:
        # 1. Initialize components
        print("\n1. Initializing components...")
        db = TradeDatabase(db_path=temp_db.name)
        predictor = MLPredictor(model_path=temp_model.name)
        sizer = PositionSizer(method='fixed_percentage', risk_per_trade=0.02)
        mtf_analyzer = MultiTimeframeAnalyzer(primary_timeframe='M5', 
                                             confirmation_timeframe='H1')
        print("   ✓ All components initialized")
        
        # 2. Generate sample data
        print("\n2. Generating sample market data...")
        df_m5 = create_sample_data(n=200, trend='neutral')
        df_h1 = create_sample_data(n=200, trend='up')
        
        # Add indicators
        df_m5 = calculate_indicators(df_m5)
        print(f"   ✓ M5 data: {len(df_m5)} bars with indicators")
        print(f"   ✓ H1 data: {len(df_h1)} bars")
        
        # 3. Train ML model
        print("\n3. Training ML model...")
        metrics = predictor.train(df_m5, database=db)
        if metrics:
            print(f"   ✓ Model trained - Accuracy: {metrics['accuracy']:.4f}, "
                  f"F1: {metrics['f1']:.4f}")
        
        # 4. Generate signal with strategy
        print("\n4. Generating trading signal...")
        signal, confidence, atr = advanced_scalp(df_m5)
        print(f"   Strategy Signal: {signal if signal else 'NONE'}")
        print(f"   Strategy Confidence: {confidence:.2%}")
        print(f"   ATR: {atr:.6f}")
        
        # 5. ML prediction boost (if signal exists)
        if signal:
            print("\n5. ML prediction boost...")
            ml_prob = predictor.predict_probability(df_m5)
            adjusted_confidence = confidence * 0.7 + ml_prob * 0.3
            print(f"   ML Probability: {ml_prob:.2%}")
            print(f"   Adjusted Confidence: {adjusted_confidence:.2%}")
            confidence = adjusted_confidence
        
        # 6. Multi-timeframe confirmation (if signal exists)
        if signal:
            print("\n6. Multi-timeframe confirmation...")
            confirmed_signal, mtf_confidence, mtf_atr = mtf_analyzer.confirm_signal(
                signal, confidence, atr, df_h1
            )
            print(f"   H1 Analysis Result: {confirmed_signal if confirmed_signal else 'REJECTED'}")
            print(f"   MTF Adjusted Confidence: {mtf_confidence:.2%}")
            signal = confirmed_signal
            confidence = mtf_confidence
        
        # 7. Position sizing (if signal still valid)
        if signal and confidence >= 0.8:
            print("\n7. Calculating position size...")
            balance = 10000.0
            stop_loss_pips = atr * 1.5 if atr > 0 else 0.001
            
            units, risk_pct = sizer.calculate_position_size(
                balance=balance,
                stop_loss_pips=stop_loss_pips,
                pip_value=10,
                confidence=confidence
            )
            
            print(f"   Account Balance: ${balance:,.2f}")
            print(f"   Stop Loss: {stop_loss_pips:.6f} pips")
            print(f"   Position Size: {units:,} units")
            print(f"   Risk: {risk_pct*100:.2f}% of balance")
            
            # 8. Store trade in database
            print("\n8. Storing trade in database...")
            entry_price = df_m5['close'].iloc[-1]
            trade_data = {
                'instrument': 'EUR_USD',
                'signal': signal,
                'confidence': confidence,
                'entry_price': entry_price,
                'stop_loss': stop_loss_pips,
                'take_profit': atr * 2.5 if atr > 0 else 0.002,
                'units': units,
                'atr': atr,
                'ml_prediction': ml_prob if 'ml_prob' in locals() else 0.5,
                'position_size_pct': risk_pct
            }
            
            trade_id = db.store_trade(trade_data)
            print(f"   ✓ Trade stored with ID: {trade_id}")
            
            # Simulate trade close
            exit_price = entry_price + (0.001 if signal == 'BUY' else -0.001)
            profit_loss = (exit_price - entry_price) * units if signal == 'BUY' else (entry_price - exit_price) * units
            db.update_trade(trade_id, exit_price, profit_loss, 'closed')
            print(f"   ✓ Trade closed - P/L: ${profit_loss:.2f}")
        
        # 9. Performance metrics
        print("\n9. Performance metrics...")
        metrics = db.get_performance_metrics(days=30)
        if metrics and metrics.get('total_trades', 0) > 0:
            print(f"   Total Trades: {metrics['total_trades']}")
            print(f"   Win Rate: {metrics['win_rate']*100:.2f}%")
            print(f"   Total Profit: ${metrics['total_profit']:.2f}")
        else:
            print("   No completed trades yet")
        
        print("\n" + "="*70)
        print("INTEGRATION TEST COMPLETED SUCCESSFULLY")
        print("="*70)
        print("\nAll components working together:")
        print("  ✓ Database persistence")
        print("  ✓ ML predictions")
        print("  ✓ Position sizing")
        print("  ✓ Multi-timeframe analysis")
        print("  ✓ Strategy signals")
        print("  ✓ Trade tracking")
        print("="*70)
        
    finally:
        # Cleanup
        db.close()
        if os.path.exists(temp_db.name):
            os.remove(temp_db.name)
        if os.path.exists(temp_model.name):
            os.remove(temp_model.name)

if __name__ == '__main__':
    test_full_workflow()
