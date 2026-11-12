import pandas as pd
from src.strategy_interface import Strategy

class ATRBreakoutStrategy(Strategy):
    def __init__(self, atr_period=14, multiplier=2.0):
        self.atr_period = atr_period
        self.multiplier = multiplier
        self.data_buffer = pd.DataFrame()

    def on_tick(self, tick_data):
        pass

    def on_data(self, candle_data):
        new_row = pd.DataFrame([candle_data])
        if self.data_buffer.empty:
            self.data_buffer = new_row
        else:
            self.data_buffer = pd.concat([self.data_buffer, new_row], ignore_index=True)
        if len(self.data_buffer) > 200:
            self.data_buffer = self.data_buffer.iloc[-200:]

    def generate_signal(self):
        if len(self.data_buffer) < self.atr_period + 1:
            return 'HOLD'

        df = self.data_buffer.copy()
        
        # Calculate ATR
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.ewm(span=self.atr_period, adjust=False).mean()
        
        current_atr = atr.iloc[-1]
        
        # Range Breakout Logic
        # If current candle body > k * ATR, it's a breakout/expansion
        body = abs(close.iloc[-1] - df['open'].iloc[-1])
        
        # We need a directional bias.
        # Breakout UP: Close > High of previous N bars?
        # Let's combine with recent price action: 
        # Buy if Close > Previous High AND Range expansion
        
        prev_high = df['high'].iloc[-2]
        prev_low = df['low'].iloc[-2]
        
        is_expansion = body > (self.multiplier * current_atr)
        
        if is_expansion and close.iloc[-1] > prev_high:
            return 'BUY'
            
        if is_expansion and close.iloc[-1] < prev_low:
            return 'SELL'
            
        return 'HOLD'
