"""
Machine Learning module for predicting signal success probability.
Uses Random Forest classifier trained on historical OHLCV data.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import pickle
import logging
import os
from datetime import datetime

class MLPredictor:
    """Machine Learning predictor for trading signals."""
    
    def __init__(self, model_path='models/rf_model.pkl'):
        self.model_path = model_path
        self.model = None
        self.scaler = StandardScaler()
        self.feature_columns = [
            'rsi', 'macd', 'macd_signal', 'atr', 'bb_width', 'volume_ratio',
            'price_change', 'high_low_range', 'close_position_in_range'
        ]
        self._ensure_model_dir()
        
    def _ensure_model_dir(self):
        """Ensure model directory exists."""
        model_dir = os.path.dirname(self.model_path)
        if model_dir and not os.path.exists(model_dir):
            os.makedirs(model_dir)
    
    def _engineer_features(self, df):
        """Engineer features from OHLCV data."""
        features = df.copy()
        
        # Price change
        features['price_change'] = (features['close'] - features['open']) / features['open']
        
        # High-low range
        features['high_low_range'] = (features['high'] - features['low']) / features['close']
        
        # Close position in range
        features['close_position_in_range'] = (
            (features['close'] - features['low']) / (features['high'] - features['low'])
        ).fillna(0.5)
        
        # Bollinger Band width
        if 'bb_upper' in features.columns and 'bb_lower' in features.columns:
            bb_middle = (features['bb_upper'] + features['bb_lower']) / 2
            features['bb_width'] = (features['bb_upper'] - features['bb_lower']) / bb_middle
        else:
            features['bb_width'] = 0.0
        
        # Volume ratio
        if 'volume' in features.columns:
            volume_ma = features['volume'].rolling(20).mean()
            features['volume_ratio'] = features['volume'] / volume_ma
            features['volume_ratio'] = features['volume_ratio'].fillna(1.0)
        else:
            features['volume_ratio'] = 1.0
        
        return features
    
    def _create_labels(self, df, future_periods=5, profit_threshold=0.0002):
        """
        Create labels for training based on future price movement.
        Label 1: Profitable trade (price moves favorably)
        Label 0: Unprofitable trade
        """
        labels = []
        
        for i in range(len(df) - future_periods):
            current_price = df.iloc[i]['close']
            future_prices = df.iloc[i+1:i+future_periods+1]['close']
            
            # Check if price moves favorably (simplified for now)
            max_future = future_prices.max()
            min_future = future_prices.min()
            
            # For a BUY signal, we want price to go up
            up_move = (max_future - current_price) / current_price
            # For a SELL signal, we want price to go down
            down_move = (current_price - min_future) / current_price
            
            # Label as 1 if either direction shows profit potential
            if up_move > profit_threshold or down_move > profit_threshold:
                labels.append(1)
            else:
                labels.append(0)
        
        # Pad the last few entries with 0 (can't predict future)
        labels.extend([0] * future_periods)
        
        return np.array(labels)
    
    def train(self, df, database=None):
        """
        Train the Random Forest model on historical data.
        
        Args:
            df: DataFrame with OHLCV data and indicators
            database: Optional database instance to store training results
        """
        logging.info("Starting ML model training...")
        
        # Engineer features
        features_df = self._engineer_features(df)
        
        # Create labels
        labels = self._create_labels(df)
        
        # Select feature columns
        X = features_df[self.feature_columns].fillna(0)
        y = labels
        
        # Ensure we have matching lengths
        min_len = min(len(X), len(y))
        X = X.iloc[:min_len]
        y = y[:min_len]
        
        if len(X) < 50:
            logging.warning("Insufficient data for training (need at least 50 samples)")
            return None
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y if len(np.unique(y)) > 1 else None
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train Random Forest
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=10,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1
        )
        
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_test_scaled)
        
        metrics = {
            'model_type': 'RandomForest',
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, zero_division=0),
            'recall': recall_score(y_test, y_pred, zero_division=0),
            'f1': f1_score(y_test, y_pred, zero_division=0),
            'training_samples': len(X_train),
            'parameters': {
                'n_estimators': 100,
                'max_depth': 10,
                'min_samples_split': 10,
                'min_samples_leaf': 5
            }
        }
        
        logging.info(f"Model training complete - Accuracy: {metrics['accuracy']:.4f}, "
                    f"Precision: {metrics['precision']:.4f}, "
                    f"Recall: {metrics['recall']:.4f}, "
                    f"F1: {metrics['f1']:.4f}")
        
        # Store training results in database
        if database:
            database.store_model_training(metrics)
        
        # Save model
        self.save_model()
        
        return metrics
    
    def predict_probability(self, df):
        """
        Predict success probability for a signal.
        
        Args:
            df: DataFrame with current market data and indicators
            
        Returns:
            Probability of successful trade (0.0 to 1.0)
        """
        if self.model is None:
            if os.path.exists(self.model_path):
                self.load_model()
            else:
                logging.warning("ML model not trained or loaded. Returning default probability.")
                return 0.5
        
        # Engineer features
        features_df = self._engineer_features(df)
        
        # Get the latest row features
        X = features_df[self.feature_columns].iloc[-1:].fillna(0)
        
        # Scale
        X_scaled = self.scaler.transform(X)
        
        # Predict probability
        prob = self.model.predict_proba(X_scaled)[0][1]  # Probability of class 1 (successful)
        
        return prob
    
    def save_model(self):
        """Save the trained model and scaler to disk."""
        if self.model is None:
            logging.warning("No model to save")
            return
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_columns': self.feature_columns,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(self.model_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        logging.info(f"Model saved to {self.model_path}")
    
    def load_model(self):
        """Load a trained model from disk."""
        if not os.path.exists(self.model_path):
            logging.warning(f"Model file not found: {self.model_path}")
            return False
        
        with open(self.model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.feature_columns = model_data.get('feature_columns', self.feature_columns)
        
        logging.info(f"Model loaded from {self.model_path}")
        return True
    
    def needs_retraining(self, min_samples=200):
        """
        Check if model needs retraining based on available data.
        
        Args:
            min_samples: Minimum number of new samples to trigger retraining
            
        Returns:
            Boolean indicating if retraining is needed
        """
        # In a real implementation, this would check the database for new data
        # For now, return False to avoid automatic retraining
        return False
