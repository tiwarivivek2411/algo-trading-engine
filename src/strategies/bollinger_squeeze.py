import pandas as pd
import numpy as np
from src.strategy_interface import Strategy

class BollingerSqueezeStrategy(Strategy):
    def __init__(self, period=20, std_dev=2, squeeze_threshold=0.10):
        self.period = period
        self.std_dev = std_dev
        self.squeeze_threshold = squeeze_threshold
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
        
        # Calculate Bollinger Bands
        df['sma'] = df['close'].rolling(window=self.period).mean()
        df['std'] = df['close'].rolling(window=self.period).std()
        df['upper'] = df['sma'] + (self.std_dev * df['std'])
        df['lower'] = df['sma'] - (self.std_dev * df['std'])
        
        # Calculate Bandwidth
        df['bandwidth'] = (df['upper'] - df['lower']) / df['sma']
        
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Logic: 
        # Check if we were in a squeeze recently (e.g., previous candle)
        was_squeeze = prev['bandwidth'] < self.squeeze_threshold
        
        # Breakout
        if was_squeeze and current['close'] > current['upper']:
            return 'BUY'
            
        if was_squeeze and current['close'] < current['lower']:
            return 'SELL'
            
        return 'HOLD'
