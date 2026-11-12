import pandas as pd
from src.strategy_interface import Strategy

class CCIStrategy(Strategy):
    def __init__(self, period=20):
        self.period = period
        self.data_buffer = pd.DataFrame()

    def on_tick(self, tick_data):
        pass

    def on_data(self, candle_data):
        new_row = pd.DataFrame([candle_data])
        if self.data_buffer.empty:
            self.data_buffer = new_row
        else:
            self.data_buffer = pd.concat([self.data_buffer, new_row], ignore_index=True)
        if len(self.data_buffer) > 100:
            self.data_buffer = self.data_buffer.iloc[-100:]

    def generate_signal(self):
        if len(self.data_buffer) < self.period:
            return 'HOLD'

        df = self.data_buffer.copy()
        
        # Calculate CCI
        # TP = (High + Low + Close) / 3
        # CCI = (TP - SMA(TP)) / (0.015 * MeanDeviation(TP))
        
        tp = (df['high'] + df['low'] + df['close']) / 3
        sma_tp = tp.rolling(window=self.period).mean()
        mad = tp.rolling(window=self.period).apply(lambda x: pd.Series(x).mad())
        # Note: pandas rolling apply mad might be deprecated or slow, but standard deviation is not the same.
        # Mean Absolute Deviation.
        # Alternative: (x - x.mean()).abs().mean()
        
        # Manual MAD rolling
        # For efficiency we might approximate or use std dev? 
        # Standard CCI uses MAD.
        # Let's use simple loop or optimized pandas
        def rolling_mad(x):
            return (x - x.mean()).abs().mean()
            
        mad = tp.rolling(window=self.period).apply(rolling_mad, raw=False)
        
        df['cci'] = (tp - sma_tp) / (0.015 * mad)
        
        curr_cci = df['cci'].iloc[-1]
        prev_cci = df['cci'].iloc[-2]
        
        # Logic:
        # Buy: CCI crosses above 100 (Momentum) or -100 (Reversal)?
        # Standard Momentum: Buy when CCI > 100 (Strong Up), Sell when CCI < -100 (Strong Down).
        
        # Let's do Standard Momentum Breakout
        if prev_cci <= 100 and curr_cci > 100:
            return 'BUY'
            
        if prev_cci >= -100 and curr_cci < -100:
            return 'SELL'
            
        return 'HOLD'
