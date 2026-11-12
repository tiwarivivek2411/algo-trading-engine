import pandas as pd
from src.base_algorithm import BaseAlgorithm

class StochasticAlgorithm(BaseAlgorithm):
    def __init__(self, k_period=14, d_period=3, aggressive=False):
        self.k_period = k_period
        self.d_period = d_period
        self.aggressive = aggressive
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
        if len(self.data_buffer) < self.k_period + self.d_period + 2:
            return 'HOLD'

        df = self.data_buffer.copy()
        low_min = df['low'].rolling(window=self.k_period).min()
        high_max = df['high'].rolling(window=self.k_period).max()
        df['k'] = 100 * ((df['close'] - low_min) / (high_max - low_min))
        df['d'] = df['k'].rolling(window=self.d_period).mean()

        current = df.iloc[-1]
        prev = df.iloc[-2]

        # Standard Crossover
        if prev['k'] <= prev['d'] and current['k'] > current['d']:
            if self.aggressive: return 'BULLISH'
            if current['k'] < 80: return 'BULLISH' # Filter OB in standard mode
        elif prev['k'] >= prev['d'] and current['k'] < current['d']:
            if self.aggressive: return 'BEARISH'
            if current['k'] > 20: return 'BEARISH' # Filter OS in standard mode

        return 'HOLD'
