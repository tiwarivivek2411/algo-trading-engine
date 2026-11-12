import pandas as pd
from src.strategy_interface import Strategy

class MeanReversionStrategy(Strategy):
    def __init__(self, rsi_period=5, rsi_lower=30, rsi_upper=70):
        self.rsi_period = rsi_period
        self.rsi_lower = rsi_lower
        self.rsi_upper = rsi_upper
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
        if len(self.data_buffer) < self.rsi_period + 1:
            return 'HOLD'

        df = self.data_buffer.copy()
        
        # Calculate RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        current_rsi = df.iloc[-1]['rsi']

        # Logic: Buy Oversold, Sell Overbought
        if current_rsi < self.rsi_lower:
            return 'BUY'
        
        if current_rsi > self.rsi_upper:
            return 'SELL'

        return 'HOLD'
