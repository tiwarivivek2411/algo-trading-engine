import pandas as pd
import numpy as np
from src.strategy_interface import Strategy

class VWAPIntradayStrategy(Strategy):
    def __init__(self):
        self.data_buffer = pd.DataFrame()
        # In a real system, VWAP resets daily. Backtester feeds continuous data.
        # We need to detect day change to reset VWAP calculation or assume the data feed provides 'vwap' field?
        # Angel One historical data API usually provides open, high, low, close, volume.
        # We will calculate "Rolling VWAP" or "Session VWAP" if possible.
        # For simplicity in this backtest context: Rolling VWAP of last N candles or Session based if timestamps allow.
        # Let's do a Rolling VWAP of last 50 candles to simulate intraday trends if session info is complex to parse.
        # Better: Daily Accumulated VWAP.
        pass

    def on_tick(self, tick_data):
        pass

    def on_data(self, candle_data):
        new_row = pd.DataFrame([candle_data])
        if self.data_buffer.empty:
            self.data_buffer = new_row
        else:
            self.data_buffer = pd.concat([self.data_buffer, new_row], ignore_index=True)

        # Reset buffer on new day? 
        # For Bulk Backtest we pass a chunk of data. 
        # We will calculate VWAP on the buffer we have.
        # To avoid infinite buffer, we keep last 375 (1 day of 1 min candles) or so.
        if len(self.data_buffer) > 400:
             self.data_buffer = self.data_buffer.iloc[-400:]

    def generate_signal(self):
        if len(self.data_buffer) < 5:
            return 'HOLD'

        df = self.data_buffer.copy()
        
        # Calculate VWAP (Volume Weighted Average Price)
        # VWAP = Cumulative(Price * Volume) / Cumulative(Volume)
        # Ideally reset every day. 
        # We will use the 'date' string to group.
        
        # Extract Date
        df['date'] = df['timestamp'].astype(str).str[:10]
        
        # Group by Date and calculate CumSum
        df['pv'] = df['close'] * df['volume']
        df['cum_pv'] = df.groupby('date')['pv'].cumsum()
        df['cum_vol'] = df.groupby('date')['volume'].cumsum()
        df['vwap'] = df['cum_pv'] / df['cum_vol']
        
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Logic: Price Crosses VWAP
        # Buy: Price crosses above VWAP
        # Sell: Price crosses below VWAP
        
        if prev['close'] < prev['vwap'] and current['close'] > current['vwap']:
            return 'BUY'
            
        if prev['close'] > prev['vwap'] and current['close'] < current['vwap']:
            return 'SELL'
            
        return 'HOLD'
