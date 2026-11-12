import pandas as pd
import numpy as np
from src.strategy_interface import Strategy

class SupertrendStrategy(Strategy):
    def __init__(self, period=7, multiplier=3):
        self.period = period
        self.multiplier = multiplier
        self.data_buffer = pd.DataFrame()

    def on_tick(self, tick_data):
        pass

    def on_data(self, candle_data):
        # Append new row
        new_row = pd.DataFrame([candle_data])
        
        if self.data_buffer.empty:
            self.data_buffer = new_row
        else:
            self.data_buffer = pd.concat([self.data_buffer, new_row], ignore_index=True)
            
        if len(self.data_buffer) > 200:
            self.data_buffer = self.data_buffer.iloc[-200:]

    def generate_signal(self):
        if len(self.data_buffer) < self.period + 2:
            return 'HOLD'

        df = self.data_buffer.copy()
        
        # Calculate Supertrend
        df = self.calculate_supertrend(df, self.period, self.multiplier)
        
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Logic:
        # BUY: Close crosses above Supertrend (Trend changes to Bullish)
        # SELL: Close crosses below Supertrend (Trend changes to Bearish)
        # Or simply state based: Close > Supertrend -> Check if previously was < Supertrend (Crossover)
        
        # Note: My calculate_supertrend returns 'Supertrend' line and 'Trend' boolean/direction
        
        if current['Trend'] == 1 and prev['Trend'] == -1:
            return 'BUY'
        
        if current['Trend'] == -1 and prev['Trend'] == 1:
            return 'SELL'
            
        return 'HOLD'

    def calculate_atr(self, df, period):
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.ewm(span=period, adjust=False).mean() # Using EMA smoothing for ATR
        return atr

    def calculate_supertrend(self, df, period, multiplier):
        atr = self.calculate_atr(df, period)
        
        hl2 = (df['high'] + df['low']) / 2
        basic_upperband = hl2 + (multiplier * atr)
        basic_lowerband = hl2 - (multiplier * atr)
        
        # Initialize columns
        df['Supertrend'] = 0.0
        df['Trend'] = 1 # 1 for Bullish, -1 for Bearish
        
        # Iterative calculation needed for Supertrend dynamic bands
        # Converting to numpy arrays for speed
        close = df['close'].values
        bu = basic_upperband.values
        bl = basic_lowerband.values
        st = np.zeros(len(df))
        trend = np.zeros(len(df))
        
        # Initial values
        st[0] = bu[0]
        trend[0] = 1
        
        for i in range(1, len(df)):
            # Final Upper Band
            if bu[i] < st[i-1] or close[i-1] > st[i-1]:
                fu = bu[i]
            else:
                fu = st[i-1]
                
            # Final Lower Band
            if bl[i] > st[i-1] or close[i-1] < st[i-1]:
                fl = bl[i]
            else:
                fl = st[i-1]
            
            # Trend Update
            if trend[i-1] == 1: # Uptrend
                if close[i] <= fl:
                    trend[i] = -1
                    st[i] = fu
                else:
                    trend[i] = 1
                    st[i] = fl
            else: # Downtrend
                if close[i] >= fu:
                    trend[i] = 1
                    st[i] = fl
                else:
                    trend[i] = -1
                    st[i] = fu
                    
        df['Supertrend'] = st
        df['Trend'] = trend
        return df
