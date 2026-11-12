import pandas as pd
from src.strategy_interface import Strategy

class IndexDirectionalStrategy(Strategy):
    def __init__(self, period=14, multiplier=3, instrument="EQUITY", type=None, strike_offset="ATM", trade_mode="REVERSE"):
        # Using Supertrend logic for direction
        self.period = period
        self.multiplier = multiplier
        self.instrument = instrument
        self.type = type
        self.strike_offset = strike_offset
        self.trade_mode = trade_mode
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
        if len(self.data_buffer) < self.period + 2:
            return 'HOLD'

        df = self.data_buffer.copy()
        
        # Calculate ATR and Supertrend
        # (Reusing logic for simplicity, in a real app this would be a shared utility)
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.ewm(span=self.period, adjust=False).mean()
        
        hl2 = (high + low) / 2
        basic_upperband = hl2 + (self.multiplier * atr)
        basic_lowerband = hl2 - (self.multiplier * atr)
        
        # Simple Loop (Optimized for brevity)
        trend = 1
        st = basic_upperband.iloc[0]
        
        for i in range(1, len(df)):
            curr_close = close.iloc[i]
            prev_close = close.iloc[i-1]
            bu = basic_upperband.iloc[i]
            bl = basic_lowerband.iloc[i]
            
            if trend == 1:
                if curr_close <= (st if st > bl else bl): # simplified logic
                     trend = -1
                     st = bu
                else:
                     st = max(st, bl)
            else:
                if curr_close >= (st if st < bu else bu):
                     trend = 1
                     st = bl
                else:
                     st = min(st, bu)
        
        current_spot = df.iloc[-1]['close']
        
        # Nifty Rounding (Nearest 50)
        strike = round(current_spot / 50) * 50
        
        # Signal Generation Logic
        signal = 'HOLD'
        
        if trend == 1:
            # Uptrend
            if self.instrument == "OPT":
                if self.type == "CE":
                    raw_signal = 'BUY'
                elif self.type == "PE":
                    raw_signal = 'SELL' 
            else:
                raw_signal = 'BUY'
                
        else:
            # Downtrend
            if self.instrument == "OPT":
               if self.type == "CE":
                   raw_signal = 'SELL'
               elif self.type == "PE":
                   raw_signal = 'BUY'
            else:
                raw_signal = 'SELL'

        # Apply Trade Mode Logic
        # allowed modes: "REVERSE" (Default), "LONG_ONLY", "SHORT_ONLY"
        mode = getattr(self, 'trade_mode', 'REVERSE')
        
        if mode == 'LONG_ONLY':
            if raw_signal == 'SELL': return 'EXIT' # Close Long if any, but don't Short
            if raw_signal == 'BUY': return 'BUY'
            
        if mode == 'SHORT_ONLY':
            if raw_signal == 'BUY': return 'COVER' # Close Short if any, but don't Long
            if raw_signal == 'SELL': return 'SELL' # Open Short or Hold Short
            
        return raw_signal
