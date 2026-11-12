import pandas as pd
import numpy as np
from src.strategy_interface import Strategy

class MomentumStrategy(Strategy):
    def __init__(self, rsi_period=14, rsi_overbought=60, rsi_oversold=40, macd_fast=12, macd_slow=26, macd_signal=9):
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        
        self.data_buffer = pd.DataFrame()

    def on_tick(self, tick_data):
        pass

    def on_data(self, candle_data):
        """
        Updates the data buffer with the new candle.
        candle_data: dict or Series with 'close', 'open', 'high', 'low', 'volume'
        """
        # Append new row
        new_row = pd.DataFrame([candle_data])
        
        if self.data_buffer.empty:
            self.data_buffer = new_row
        else:
            # Avoid duplicate timestamps if possible, but for MVP just append
            self.data_buffer = pd.concat([self.data_buffer, new_row], ignore_index=True)
            
        # Keep buffer size manageable (e.g., last 200 candles)
        if len(self.data_buffer) > 200:
            self.data_buffer = self.data_buffer.iloc[-200:]

    def generate_signal(self):
        if len(self.data_buffer) < 50:
            return 'HOLD'

        df = self.data_buffer.copy()
        
        # Calculate Indicators
        df['rsi'] = self.calculate_rsi(df['close'], self.rsi_period)
        macd, signal_line = self.calculate_macd(df['close'], self.macd_fast, self.macd_slow, self.macd_signal)
        df['macd'] = macd
        df['macd_signal'] = signal_line

        current = df.iloc[-1]
        prev = df.iloc[-2]

        # Logic
        # BUY: RSI > 60 AND MACD Crosses Above Signal
        # SELL: RSI < 40 AND MACD Crosses Below Signal
        
        # Check Crossover
        macd_cross_up = (prev['macd'] <= prev['macd_signal']) and (current['macd'] > current['macd_signal'])
        macd_cross_down = (prev['macd'] >= prev['macd_signal']) and (current['macd'] < current['macd_signal'])
        
        if current['rsi'] > self.rsi_overbought and macd_cross_up:
            return 'BUY'
        
        if current['rsi'] < self.rsi_oversold and macd_cross_down:
            return 'SELL'
            
        return 'HOLD'

    def calculate_rsi(self, series, period):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def calculate_macd(self, series, fast, slow, signal):
        exp1 = series.ewm(span=fast, adjust=False).mean()
        exp2 = series.ewm(span=slow, adjust=False).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        return macd, signal_line
