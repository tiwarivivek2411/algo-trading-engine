import pandas as pd
from src.strategy_interface import Strategy

class KeltnerChannelStrategy(Strategy):
    def __init__(self, ema_period=20, atr_period=10, multiplier=2.0):
        self.ema_period = ema_period
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
        if len(self.data_buffer) > 100:
            self.data_buffer = self.data_buffer.iloc[-100:]

    def generate_signal(self):
        if len(self.data_buffer) < max(self.ema_period, self.atr_period) + 2:
            return 'HOLD'

        df = self.data_buffer.copy()
        
        # EMA
        df['ema'] = df['close'].ewm(span=self.ema_period, adjust=False).mean()
        
        # ATR
        high = df['high']
        low = df['low']
        close = df['close']
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['atr'] = tr.ewm(span=self.atr_period, adjust=False).mean()
        
        # Channels
        df['upper'] = df['ema'] + (self.multiplier * df['atr'])
        df['lower'] = df['ema'] - (self.multiplier * df['atr'])
        
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Trend Following Breakout
        # Buy on Close > Upper
        # Sell on Close < Lower
        
        if prev['close'] <= prev['upper'] and current['close'] > current['upper']:
            return 'BUY'
            
        if prev['close'] >= prev['lower'] and current['close'] < current['lower']:
            return 'SELL'
            
        return 'HOLD'
