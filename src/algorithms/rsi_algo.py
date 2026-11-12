import pandas as pd
from src.base_algorithm import BaseAlgorithm

class RSIAlgorithm(BaseAlgorithm):
    def __init__(self, period=14, overbought=70, oversold=30):
        self.period = period
        self.overbought = overbought
        self.oversold = oversold
        self.data_buffer = pd.DataFrame()

    def on_data(self, candle_data: pd.Series):
        new_row = pd.DataFrame([candle_data])
        if self.data_buffer.empty:
            self.data_buffer = new_row
        else:
            self.data_buffer = pd.concat([self.data_buffer, new_row], ignore_index=True)
        if len(self.data_buffer) > 200:
            self.data_buffer = self.data_buffer.iloc[-200:]

    def generate_bias(self) -> str:
        if len(self.data_buffer) < self.period + 2:
            return 'HOLD'

        df = self.data_buffer.copy()
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        current = df.iloc[-1]['rsi']
        prev = df.iloc[-2]['rsi']

        # Reversal signals
        if prev < self.oversold and current >= self.oversold: return 'BULLISH'
        if prev > self.overbought and current <= self.overbought: return 'BEARISH'

        return 'HOLD'
