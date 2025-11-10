"""
Multi-timeframe analysis module for confirming signals across different timeframes.
"""
import logging
from strategies import get_signal_with_confidence, calculate_indicators

class MultiTimeframeAnalyzer:
    """Analyze signals across multiple timeframes for confirmation."""
    
    def __init__(self, primary_timeframe='M5', confirmation_timeframe='H1'):
        """
        Initialize multi-timeframe analyzer.
        
        Args:
            primary_timeframe: Primary timeframe for signal generation (e.g., 'M5')
            confirmation_timeframe: Higher timeframe for confirmation (e.g., 'H1')
        """
        self.primary_timeframe = primary_timeframe
        self.confirmation_timeframe = confirmation_timeframe
        
    def analyze_timeframe(self, df, strategy='advanced_scalp'):
        """
        Analyze a single timeframe and return signal with confidence.
        
        Args:
            df: DataFrame with OHLCV data
            strategy: Strategy name to use
            
        Returns:
            Tuple of (signal, confidence, atr)
        """
        signal, confidence, atr = get_signal_with_confidence(df, strategy)
        return signal, confidence, atr
    
    def get_trend_direction(self, df):
        """
        Determine overall trend direction from higher timeframe.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            'BUY' (uptrend), 'SELL' (downtrend), or None (neutral)
        """
        if len(df) < 50:
            return None
        
        # Calculate indicators for trend determination
        df_indicators = calculate_indicators(df)
        
        if df_indicators is None:
            return None
        
        latest = df_indicators.iloc[-1]
        
        # Use multiple indicators to determine trend
        trend_signals = []
        
        # 1. MACD trend
        if latest['macd'] > latest['macd_signal']:
            trend_signals.append('BUY')
        elif latest['macd'] < latest['macd_signal']:
            trend_signals.append('SELL')
        
        # 2. Price relative to Bollinger Bands middle
        if latest['close'] > latest['bb_middle']:
            trend_signals.append('BUY')
        elif latest['close'] < latest['bb_middle']:
            trend_signals.append('SELL')
        
        # 3. RSI trend (above/below 50)
        if latest['rsi'] > 50:
            trend_signals.append('BUY')
        elif latest['rsi'] < 50:
            trend_signals.append('SELL')
        
        # Determine overall trend (majority vote)
        buy_count = trend_signals.count('BUY')
        sell_count = trend_signals.count('SELL')
        
        if buy_count > sell_count:
            return 'BUY'
        elif sell_count > buy_count:
            return 'SELL'
        else:
            return None
    
    def confirm_signal(self, primary_signal, primary_confidence, primary_atr,
                       confirmation_df, strategy='advanced_scalp'):
        """
        Confirm primary timeframe signal with higher timeframe analysis.
        
        Args:
            primary_signal: Signal from primary timeframe
            primary_confidence: Confidence from primary timeframe
            primary_atr: ATR from primary timeframe
            confirmation_df: DataFrame with higher timeframe data
            strategy: Strategy to use for confirmation
            
        Returns:
            Tuple of (confirmed_signal, adjusted_confidence, atr)
        """
        if not primary_signal:
            return None, 0.0, primary_atr
        
        # Get trend from higher timeframe
        htf_trend = self.get_trend_direction(confirmation_df)
        
        # Get signal from higher timeframe
        htf_signal, htf_confidence, htf_atr = self.analyze_timeframe(
            confirmation_df, strategy
        )
        
        # Confirmation logic
        confirmed = False
        confidence_boost = 0.0
        
        # Strong confirmation: Both trend and signal align
        if htf_trend == primary_signal and htf_signal == primary_signal:
            confirmed = True
            confidence_boost = 0.15
            logging.info(f"Strong H1 confirmation: trend and signal both {primary_signal}")
        
        # Moderate confirmation: Trend aligns (even if no signal)
        elif htf_trend == primary_signal:
            confirmed = True
            confidence_boost = 0.10
            logging.info(f"Moderate H1 confirmation: trend {primary_signal}")
        
        # Weak confirmation: Signal aligns but trend is neutral
        elif htf_signal == primary_signal and htf_trend is None:
            confirmed = True
            confidence_boost = 0.05
            logging.info(f"Weak H1 confirmation: signal {primary_signal}, neutral trend")
        
        # No confirmation or contradiction
        else:
            if htf_trend and htf_trend != primary_signal:
                # Contradiction - reduce confidence
                confidence_boost = -0.15
                logging.warning(f"H1 contradiction: M5 signal {primary_signal} vs H1 trend {htf_trend}")
            else:
                # Neutral - slight reduction
                confidence_boost = -0.05
                logging.info(f"No H1 confirmation for {primary_signal}")
        
        # Adjust confidence
        adjusted_confidence = min(1.0, max(0.0, primary_confidence + confidence_boost))
        
        # If confidence drops too low, invalidate signal
        if adjusted_confidence < 0.6:
            logging.info(f"Signal rejected after H1 analysis (confidence {adjusted_confidence:.2f})")
            return None, adjusted_confidence, primary_atr
        
        return primary_signal, adjusted_confidence, primary_atr
    
    def analyze_multi_timeframe(self, primary_df, confirmation_df, strategy='advanced_scalp'):
        """
        Complete multi-timeframe analysis workflow.
        
        Args:
            primary_df: DataFrame with primary timeframe data (M5)
            confirmation_df: DataFrame with confirmation timeframe data (H1)
            strategy: Strategy to use
            
        Returns:
            Tuple of (signal, confidence, atr)
        """
        # Get primary signal
        primary_signal, primary_confidence, primary_atr = self.analyze_timeframe(
            primary_df, strategy
        )
        
        # If no primary signal, return early
        if not primary_signal:
            return None, 0.0, 0.0
        
        # Confirm with higher timeframe
        confirmed_signal, adjusted_confidence, atr = self.confirm_signal(
            primary_signal, primary_confidence, primary_atr,
            confirmation_df, strategy
        )
        
        return confirmed_signal, adjusted_confidence, atr
