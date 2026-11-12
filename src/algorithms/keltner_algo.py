import pandas as pd
from src.base_algorithm import BaseAlgorithm

class KeltnerAlgorithm(BaseAlgorithm):
    def __init__(self, ema_period=10, atr_period=10, multiplier=2.0):
        self.ema_period = ema_period
        self.atr_period = atr_period
        self.multiplier = multiplier
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
        if len(self.data_buffer) < max(self.ema_period, self.atr_period) + 2:
            return 'HOLD'

        df = self.data_buffer.copy()
        df['ema'] = df['close'].ewm(span=self.ema_period, adjust=False).mean()
        
        high, low, close = df['high'], df['low'], df['close']
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['atr'] = tr.ewm(span=self.atr_period, adjust=False).mean()
        
        df['upper'] = df['ema'] + (self.multiplier * df['atr'])
        df['lower'] = df['ema'] - (self.multiplier * df['atr'])
        
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        if prev['close'] <= prev['upper'] and current['close'] > current['upper']:
            return 'BULLISH'
        elif prev['close'] >= prev['lower'] and current['close'] < current['lower']:
            return 'BEARISH'
        
        return 'HOLD'
