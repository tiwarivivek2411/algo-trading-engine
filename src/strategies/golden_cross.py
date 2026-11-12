import pandas as pd
from src.strategy_interface import Strategy

class GoldenCrossStrategy(Strategy):
    def __init__(self, short_window=50, long_window=200):
        self.short_window = short_window
        self.long_window = long_window
        self.data_buffer = pd.DataFrame()

    def on_tick(self, tick_data):
        pass

    def on_data(self, candle_data):
        new_row = pd.DataFrame([candle_data])
        
        if self.data_buffer.empty:
            self.data_buffer = new_row
        else:
            self.data_buffer = pd.concat([self.data_buffer, new_row], ignore_index=True)
            
        # Need enough data for 200 SMA
        if len(self.data_buffer) > self.long_window + 50:
            self.data_buffer = self.data_buffer.iloc[-(self.long_window + 50):]

    def generate_signal(self):
        if len(self.data_buffer) < self.long_window:
            return 'HOLD'

        df = self.data_buffer.copy()
        
        df['sma_short'] = df['close'].rolling(window=self.short_window).mean()
        df['sma_long'] = df['close'].rolling(window=self.long_window).mean()
        
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        # BUY: Short crosses above Long (Golden Cross)
        # SELL: Short crosses below Long (Death Cross)
        
        if prev['sma_short'] <= prev['sma_long'] and current['sma_short'] > current['sma_long']:
            return 'BUY'
            
        if prev['sma_short'] >= prev['sma_long'] and current['sma_short'] < current['sma_long']:
            return 'SELL'
            
        return 'HOLD'
