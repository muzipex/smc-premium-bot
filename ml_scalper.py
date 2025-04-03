import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib
import os
import logging
from datetime import datetime

class MLScalper:
    def __init__(self):
        self.setup_logging()
        self.logger.info("Initializing ML Scalper")
        
        try:
            # Use a simpler model initially
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=5,
                min_samples_split=5,
                random_state=42,
                class_weight='balanced'
            )
            self.scaler = StandardScaler()
            self.min_samples = 100  # Reduced from 1000
            self.model_path = "models/scalper_model.joblib"
            self.feature_columns = [
                'price_range', 'volume_ratio', 'rsi', 'trend'  # Simplified features
            ]
            
            # Initialize with basic data
            self._initialize_basic_model()
                
        except Exception as e:
            self.logger.error(f"Error in initialization: {str(e)}")
            raise

    def _initialize_basic_model(self):
        """Initialize model with basic market patterns"""
        try:
            # Create simple training data
            n_samples = 200
            X = np.zeros((n_samples, len(self.feature_columns)))
            y = np.zeros(n_samples)
            
            # Generate basic patterns
            for i in range(n_samples):
                # price_range (0-1)
                X[i, 0] = np.random.uniform(0, 1)
                # volume_ratio (0.5-2.0)
                X[i, 1] = np.random.uniform(0.5, 2.0)
                # rsi (0-100)
                X[i, 2] = np.random.uniform(0, 100)
                # trend (0 or 1)
                X[i, 3] = np.random.randint(0, 2)
                
                # Generate labels based on common trading rules
                if X[i, 2] < 30 and X[i, 1] > 1.5:  # RSI oversold + high volume
                    y[i] = 1  # Buy
                elif X[i, 2] > 70 and X[i, 1] > 1.5:  # RSI overbought + high volume
                    y[i] = 2  # Sell
                    
            # Fit scaler and model
            self.scaler.fit(X)
            self.model.fit(X, y)
            
            self.logger.info("Model initialized with basic patterns")
            
        except Exception as e:
            self.logger.error(f"Error in basic initialization: {e}")
            raise

    def setup_logging(self):
        self.logger = logging.getLogger('MLScalper')
        self.logger.setLevel(logging.DEBUG)
        
        if not self.logger.handlers:
            # File handler
            fh = logging.FileHandler('ml_scalper.log')
            fh.setLevel(logging.DEBUG)
            
            # Console handler
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            
            # Formatter
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            fh.setFormatter(formatter)
            ch.setFormatter(formatter)
            
            self.logger.addHandler(fh)
            self.logger.addHandler(ch)

    def load_model(self):
        """Load pre-trained model if exists"""
        try:
            if os.path.exists(self.model_path):
                model_data = joblib.load(self.model_path)
                if isinstance(model_data, tuple) and len(model_data) == 2:
                    self.model, self.scaler = model_data
                    self.logger.info("Model loaded successfully")
                    return True
                else:
                    self.logger.warning("Invalid model file format")
            else:
                self.logger.info("No pre-trained model found")
            return False
        except Exception as e:
            self.logger.error(f"Error loading model: {str(e)}")
            return False

    def calculate_rsi(self, prices, period=14):
        """Calculate Relative Strength Index"""
        try:
            # Calculate price differences
            delta = prices.diff()
            
            # Separate gains and losses
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            # Calculate RS and RSI
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            # Handle edge cases
            rsi = rsi.replace([np.inf, -np.inf], np.nan)
            rsi = rsi.fillna(50)  # Fill NaN with neutral value
            
            return rsi
            
        except Exception as e:
            self.logger.error(f"Error calculating RSI: {e}")
            return pd.Series(50, index=prices.index)  # Return neutral RSI on error

    def calculate_macd(self, prices, fast=12, slow=26, signal=9):
        """Calculate MACD indicator"""
        try:
            # Calculate EMAs
            ema_fast = prices.ewm(span=fast, adjust=False).mean()
            ema_slow = prices.ewm(span=slow, adjust=False).mean()
            
            # Calculate MACD and Signal line
            macd = ema_fast - ema_slow
            signal_line = macd.ewm(span=signal, adjust=False).mean()
            
            return macd, signal_line
            
        except Exception as e:
            self.logger.error(f"Error calculating MACD: {e}")
            return pd.Series(0, index=prices.index), pd.Series(0, index=prices.index)

    def prepare_features(self, df):
        """Fixed feature preparation with proper indexing"""
        try:
            df = df.copy()
            
            # Basic features with error checking
            df['price_range'] = df.apply(lambda x: (x['high'] - x['low']) / x['close'] if x['close'] != 0 else 0, axis=1)
            
            # Volume features with safe calculations
            volume_ma = df['tick_volume'].rolling(20).mean()
            df['volume_ratio'] = df['tick_volume'] / volume_ma.where(volume_ma != 0, 1)
            
            # Technical indicators
            df['rsi'] = self.calculate_rsi(df['close'])
            df['trend'] = (df['close'] > df['close'].rolling(20).mean()).astype(float)
            
            # Forward fill NaN values first, then fill remaining with 0
            df = df.ffill().fillna(0)
            
            # Ensure all required features exist and are numeric
            for col in self.feature_columns:
                if col not in df.columns:
                    df[col] = 0
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            # Convert to numpy array for prediction
            features = df[self.feature_columns].astype(float)
            
            return features
            
        except Exception as e:
            self.logger.error(f"Error in prepare_features: {str(e)}")
            self.logger.error(f"Available columns: {df.columns.tolist()}")
            raise

    def calculate_atr(self, df, period=14):
        """Calculate Average True Range"""
        try:
            high = df['high']
            low = df['low']
            close = df['close']
            
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            
            tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
            atr = tr.rolling(window=period).mean()
            
            return atr
        except Exception as e:
            self.logger.error(f"Error calculating ATR: {str(e)}")
            return pd.Series(0, index=df.index)

    def create_labels(self, df, pip_threshold=10):
        """Create labels based on profitable patterns"""
        try:
            df['signal'] = 0  # Neutral
            
            # Look for stronger moves (10 pips)
            future_high = df['high'].shift(-3).rolling(3).max()
            future_low = df['low'].shift(-3).rolling(3).min()
            
            current_price = df['close']
            pip_value = current_price * 0.0001
            
            # Buy signals when:
            buy_conditions = (
                (df['rsi'] < 30) &  # Oversold
                (df['volume_ratio'] > 1.2) &  # High volume
                (df['price_position'] < 0.3) &  # Near support
                (df['trend'] == 1)  # Uptrend
            )
            
            # Sell signals when:
            sell_conditions = (
                (df['rsi'] > 70) &  # Overbought
                (df['volume_ratio'] > 1.2) &  # High volume
                (df['price_position'] > 0.7) &  # Near resistance
                (df['trend'] == 0)  # Downtrend
            )
            
            df.loc[buy_conditions, 'signal'] = 1
            df.loc[sell_conditions, 'signal'] = 2
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error in create_labels: {str(e)}")
            raise

    def predict(self, df):
        """Fixed prediction with proper array handling"""
        try:
            # Prepare features and ensure numpy array
            features = self.prepare_features(df)
            
            if len(features) == 0:
                return None, 0
                
            # Get last row for prediction
            X = features.iloc[-1:].values if isinstance(features, pd.DataFrame) else features[-1:].reshape(1, -1)
            
            # Scale features
            X = self.scaler.transform(X)
            
            # Make prediction
            prediction = self.model.predict(X)[0]
            probs = self.model.predict_proba(X)[0]
            
            # Calculate confidence
            confidence = float(probs[prediction] * 100)
            
            # Add confidence boosters
            if prediction == 1:  # BUY
                rsi_value = float(df['rsi'].iloc[-1])
                if rsi_value < 30:
                    confidence += 20
                volume_ratio = float(df['volume_ratio'].iloc[-1])
                if volume_ratio > 1.5:
                    confidence += 10
                    
            elif prediction == 2:  # SELL
                rsi_value = float(df['rsi'].iloc[-1])
                if rsi_value > 70:
                    confidence += 20
                volume_ratio = float(df['volume_ratio'].iloc[-1])
                if volume_ratio > 1.5:
                    confidence += 10
            
            confidence = min(confidence, 100)
            
            self.logger.info(f"Prediction details - Type: {prediction}, Confidence: {confidence:.2f}%")
            
            if prediction == 1 and confidence > 30:
                return "BUY", confidence
            elif prediction == 2 and confidence > 30:
                return "SELL", confidence
            
            return None, 0
            
        except Exception as e:
            self.logger.error(f"Error in predict: {str(e)}")
            return None, 0
