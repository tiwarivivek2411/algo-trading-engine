import pandas as pd
from src.strategy_interface import Strategy

class DonchianChannelStrategy(Strategy):
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
        if len(self.data_buffer) > self.period + 50:
            self.data_buffer = self.data_buffer.iloc[-(self.period + 50):]

    def generate_signal(self):
        if len(self.data_buffer) < self.period + 1:
            return 'HOLD'

        df = self.data_buffer.copy()
        
        # Donchian Channels: Max High / Min Low of last N periods (excluding current)
        # We use shift(1) so we compare current price to previous N highs
        df['upper'] = df['high'].shift(1).rolling(window=self.period).max()
        df['lower'] = df['low'].shift(1).rolling(window=self.period).min()
        
        current = df.iloc[-1]
        
        # Breakout Logic (Turtle Style)
        # Buy if Close > Upper Channel
        # Sell if Close < Lower Channel
        
        if current['close'] > current['upper']:
            return 'BUY'
            
        if current['close'] < current['lower']:
            return 'SELL'
            
        return 'HOLD'
