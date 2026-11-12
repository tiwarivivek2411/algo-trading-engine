import pandas as pd
from src.strategy_interface import Strategy

class ParabolicSARStrategy(Strategy):
    def __init__(self, step=0.02, max_step=0.2):
        self.step = step
        self.max_step = max_step
        self.data_buffer = pd.DataFrame()
        # SAR state needs persistence across generates
        self.sar = 0.0
        self.af = 0.0
        self.trend = 0 # 1 Up, -1 Down
        self.ep = 0.0 # Extreme Point

    def on_tick(self, tick_data):
        pass

    def on_data(self, candle_data):
        new_row = pd.DataFrame([candle_data])
        if self.data_buffer.empty:
            self.data_buffer = new_row
            # Init SAR logic on first candle? 
            # Usually needs a few candles to determine initial trend.
            # Simplified: assume trend based on open/close
            self.trend = 1 if candle_data['close'] > candle_data['open'] else -1
            self.sar = candle_data['low'] if self.trend == 1 else candle_data['high']
            self.ep = candle_data['high'] if self.trend == 1 else candle_data['low']
            self.af = self.step
        else:
            self.data_buffer = pd.concat([self.data_buffer, new_row], ignore_index=True)
            self._update_sar(candle_data)
            
        if len(self.data_buffer) > 100:
            self.data_buffer = self.data_buffer.iloc[-100:]

    def _update_sar(self, candle):
        # Calculation of next SAR based on previous values
        # PSAR(t) = PSAR(t-1) + AF * (EP - PSAR(t-1))
        
        # Logic is tricky to implement perfectly in 'on_data' without full history replay 
        # because Backtester calls on_data candle by candle.
        # But wait, self.sar stored IS the sar for the *current* candle we just received?
        # No, SAR is calculated for *tomorrow* based on *today*. 
        # Or SAR for *today* is known at open.
        
        # Let's align: self.sar is the value valid for the candle 'candle' passed in.
        # After processing 'candle', we calculate next_sar.
        
        high = candle['high']
        low = candle['low']
        
        # Update AF and EP
        if self.trend == 1:
            if high > self.ep:
                self.ep = high
                self.af = min(self.af + self.step, self.max_step)
        else:
             if low < self.ep:
                 self.ep = low
                 self.af = min(self.af + self.step, self.max_step)
                 
        next_sar = self.sar + self.af * (self.ep - self.sar)
        
        # Constraint: SAR cannot be greater than prev Low (uptrend) or lower than prev High (downtrend)
        # Actually usually checked against last 2 bars.
        
        # Check Reversal for NEXT candle
        # If trend is UP, and Low < SAR -> Reverse to Down
        pass 
        # This implementation requires careful state management. 
        # For simplicity in this factory, we will use pandas TA or simple iterative calc in generate_signal
        # relying on the buffer. It's safer than stateful class if backtester resets/instantiates.
    
    def generate_signal(self):
        if len(self.data_buffer) < 5:
            return 'HOLD'
            
        # Re-calc SAR on full buffer to ensure correctness without rigorous state persistence issues
        # This is strictly slower but robust for backtesting script which might not persist state perfectly if re-instantiated.
        
        df = self.data_buffer.copy()
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        
        # Simple TA-Lib style SAR implementation in python
        # Initial Trend
        trend = [0] * len(df)
        sar = [0.0] * len(df)
        ep = [0.0] * len(df)
        af = [0.0] * len(df)
        
        # Init
        trend[0] = 1 if close[0] > df['open'].values[0] else -1
        sar[0] = low[0] if trend[0] == 1 else high[0]
        ep[0] = high[0] if trend[0] == 1 else low[0]
        af[0] = self.step
        
        for i in range(1, len(df)):
            prev_sar = sar[i-1]
            prev_trend = trend[i-1]
            prev_ep = ep[i-1]
            prev_af = af[i-1]
            
            # Calculate tentative SAR
            temp_sar = prev_sar + prev_af * (prev_ep - prev_sar)
            
            curr_trend = prev_trend
            curr_af = prev_af
            curr_ep = prev_ep
            
            if prev_trend == 1: # Uptrend
                # Check reversal
                if low[i] < temp_sar:
                    curr_trend = -1
                    sar[i] = prev_ep # SAR becomes EP (extreme high)
                    curr_ep = low[i]
                    curr_af = self.step
                else:
                    sar[i] = temp_sar
                    if high[i] > prev_ep:
                        curr_ep = high[i]
                        curr_af = min(prev_af + self.step, self.max_step)
                        
            else: # Downtrend
                if high[i] > temp_sar:
                    curr_trend = 1
                    sar[i] = prev_ep # SAR becomes EP (extreme low)
                    curr_ep = high[i]
                    curr_af = self.step
                else:
                    sar[i] = temp_sar
                    if low[i] < prev_ep:
                        curr_ep = low[i]
                        curr_af = min(prev_af + self.step, self.max_step)
            
            trend[i] = curr_trend
            ep[i] = curr_ep
            af[i] = curr_af
            
        current_trend = trend[-1]
        prev_trend = trend[-2]
        
        # Signal on Reversal
        if prev_trend == -1 and current_trend == 1:
            return 'BUY'
            
        if prev_trend == 1 and current_trend == -1:
            return 'SELL'
            
        return 'HOLD'
