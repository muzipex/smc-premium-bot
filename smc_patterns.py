import pandas as pd
import numpy as np

class SMCPatterns:
    @staticmethod
    def find_equal_highs(df, lookback=5, threshold=0.0002):
        highs = df['high'].values
        equal_highs = []
        for i in range(len(highs)-lookback, len(highs)-1):
            if abs(highs[i] - highs[i+1]) <= threshold:
                equal_highs.append(i)
        return len(equal_highs) > 0

    @staticmethod
    def find_equal_lows(df, lookback=5, threshold=0.0002):
        lows = df['low'].values
        equal_lows = []
        for i in range(len(lows)-lookback, len(lows)-1):
            if abs(lows[i] - lows[i+1]) <= threshold:
                equal_lows.append(i)
        return len(equal_lows) > 0

    @staticmethod
    def calculate_pattern_confidence(df):
        # Calculate confidence score (0-100)
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values
        volumes = df['tick_volume'].values
        
        confidence = 0
        
        # Volume confidence (0-30 points)
        vol_avg = np.mean(volumes[-5:])
        if volumes[-1] > vol_avg * 1.5:
            confidence += 30
        elif volumes[-1] > vol_avg * 1.2:
            confidence += 20
        elif volumes[-1] > vol_avg:
            confidence += 10
            
        # Price action confidence (0-40 points)
        candle_size = abs(closes[-1] - df['open'].values[-1])
        avg_candle = np.mean([abs(closes[i] - df['open'].values[i]) for i in range(-5, -1)])
        if candle_size > avg_candle * 1.5:
            confidence += 40
        elif candle_size > avg_candle:
            confidence += 20
            
        # Trend confirmation (0-30 points)
        if all(closes[-3:] > closes[-4:-1]) or all(closes[-3:] < closes[-4:-1]):
            confidence += 30
        elif closes[-1] > closes[-2] or closes[-1] < closes[-2]:
            confidence += 15

        # Add momentum analysis (0-20 points)
        roc = (df['close'].values[-1] / df['close'].values[-5] - 1) * 100
        if abs(roc) > 0.5:  # Strong momentum
            confidence += 20
        elif abs(roc) > 0.2:  # Moderate momentum
            confidence += 10
            
        return min(confidence, 100)

    @staticmethod
    def calculate_trend_strength(df, period=14):
        closes = df['close'].values
        sma = pd.Series(closes).rolling(period).mean().values
        
        # Calculate trend strength based on distance from SMA
        strength = abs(closes[-1] - sma[-1]) / sma[-1] * 100
        trend_direction = 1 if closes[-1] > sma[-1] else -1
        
        return strength * trend_direction

    def detect_premium_entry(self, df):
        """Enhanced SMC pattern detection"""
        try:
            if len(df) < 20:  # Need enough data
                return None, 0

            highs = df['high'].values
            lows = df['low'].values
            closes = df['close'].values
            volumes = df['tick_volume'].values
            
            # Calculate SMC signals
            trend_strength = self.calculate_trend_strength(df)
            volume_trend = volumes[-1] > volumes[-2] > volumes[-3]
            price_momentum = abs(closes[-1] - closes[-5]) / closes[-5] * 100
            
            # Find key levels
            recent_high = max(highs[-5:])
            recent_low = min(lows[-5:])
            
            # Premium buy zone
            if (lows[-1] < recent_low and 
                closes[-1] > lows[-1] and 
                volume_trend and 
                trend_strength > 0):
                confidence = min(70 + price_momentum, 100)
                return "BUY", confidence
                
            # Premium sell zone
            if (highs[-1] > recent_high and 
                closes[-1] < highs[-1] and 
                volume_trend and 
                trend_strength < 0):
                confidence = min(70 + price_momentum, 100)
                return "SELL", confidence
                
            return None, 0
            
        except Exception as e:
            print(f"Error in detect_premium_entry: {e}")
            return None, 0
