import pandas as pd
from src.strategy_interface import Strategy

class PriceActionStrategy(Strategy):
    def __init__(self, pattern="BOTH"):
        # pattern: 'INSIDE_BAR', 'ENGULFING', 'BOTH'
        self.pattern = pattern
        self.data_buffer = pd.DataFrame()

    def on_tick(self, tick_data):
        pass

    def on_data(self, candle_data):
        new_row = pd.DataFrame([candle_data])
        if self.data_buffer.empty:
            self.data_buffer = new_row
        else:
            self.data_buffer = pd.concat([self.data_buffer, new_row], ignore_index=True)
        if len(self.data_buffer) > 10:
            self.data_buffer = self.data_buffer.iloc[-10:]

    def generate_signal(self):
        if len(self.data_buffer) < 3:
            return 'HOLD'

        df = self.data_buffer.copy()
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        
        signal = 'HOLD'
        
        # Inside Bar Logic
        # Current bar is completely inside Previous bar
        is_inside = (curr['high'] < prev['high']) and (curr['low'] > prev['low'])
        
        # Engulfing Logic
        # Bullish: Prev Red, Curr Green, Curr range engulfs Prev body
        prev_body = abs(prev['close'] - prev['open'])
        curr_body = abs(curr['close'] - curr['open'])
        
        is_green = curr['close'] > curr['open']
        prev_red = prev['close'] < prev['open']
        
        is_bull_engulf = prev_red and is_green and (curr['close'] > prev['open']) and (curr['open'] < prev['close'])
        is_bear_engulf = (not prev_red) and (not is_green) and (curr['close'] < prev['open']) and (curr['open'] > prev['close'])

        if self.pattern in ["INSIDE_BAR", "BOTH"]:
            if is_inside:
                # Inside bar is a setup, usually trade the breakout of it.
                # For simplicity here, we assume it continues the prev trend or we wait for next?
                # Actually, Inside Bar is consolidation. We need the NEXT candle to break out.
                # To keep it simple for this framework: 
                # If we detect Inside Bar, we can't trade immediately without Pending Order support.
                # So we will trade Engulfing primarily for Market Execution in this simple engine.
                pass

        if self.pattern in ["ENGULFING", "BOTH"]:
            if is_bull_engulf:
                signal = 'BUY'
            elif is_bear_engulf:
                signal = 'SELL'
                
        return signal
