import pandas as pd
from src.strategy_interface import Strategy

class StochasticOscillatorStrategy(Strategy):
    def __init__(self, k_period=14, d_period=3, overbought=80, oversold=20):
        self.k_period = k_period
        self.d_period = d_period
        self.overbought = overbought
        self.oversold = oversold
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
        if len(self.data_buffer) < self.k_period + self.d_period:
            return 'HOLD'

        df = self.data_buffer.copy()
        
        # Calculate %K
        low_min = df['low'].rolling(window=self.k_period).min()
        high_max = df['high'].rolling(window=self.k_period).max()
        
        df['k'] = 100 * ((df['close'] - low_min) / (high_max - low_min))
        
        # Calculate %D (SMA of %K)
        df['d'] = df['k'].rolling(window=self.d_period).mean()
        
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Logic: 
        # Buy: %K crosses above %D in Oversold territory (< 20)
        # Sell: %K crosses below %D in Overbought territory (> 80)
        
        # Bullish Crossover in Oversold
        if prev['k'] < prev['d'] and curr['k'] > curr['d'] and curr['k'] < self.oversold:
            return 'BUY'
            
        # Bearish Crossover in Overbought
        if prev['k'] > prev['d'] and curr['k'] < curr['d'] and curr['k'] > self.overbought:
            return 'SELL'
            
        return 'HOLD'
