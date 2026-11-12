import pandas as pd
import numpy as np
from src.strategy_interface import Strategy

class ADXTrendStrategy(Strategy):
    def __init__(self, adx_period=14, adx_threshold=25):
        self.period = adx_period
        self.threshold = adx_threshold
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
        if len(self.data_buffer) < self.period * 2:
            return 'HOLD'

        df = self.data_buffer.copy()
        
        # Calculate True Range and Directional Move
        df['tr0'] = abs(df['high'] - df['low'])
        df['tr1'] = abs(df['high'] - df['close'].shift(1))
        df['tr2'] = abs(df['low'] - df['close'].shift(1))
        df['tr'] = df[['tr0', 'tr1', 'tr2']].max(axis=1)
        
        df['up_move'] = df['high'] - df['high'].shift(1)
        df['down_move'] = df['low'].shift(1) - df['low']
        
        df['plus_dm'] = np.where((df['up_move'] > df['down_move']) & (df['up_move'] > 0), df['up_move'], 0)
        df['minus_dm'] = np.where((df['down_move'] > df['up_move']) & (df['down_move'] > 0), df['down_move'], 0)

        # Smoothed
        df['atr'] = df['tr'].ewm(alpha=1/self.period, adjust=False).mean()
        df['plus_di'] = 100 * (df['plus_dm'].ewm(alpha=1/self.period, adjust=False).mean() / df['atr'])
        df['minus_di'] = 100 * (df['minus_dm'].ewm(alpha=1/self.period, adjust=False).mean() / df['atr'])
        
        df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
        df['adx'] = df['dx'].ewm(alpha=1/self.period, adjust=False).mean()
        
        current = df.iloc[-1]
        
        # Logic: 
        # Strong Trend (ADX > Threshold)
        # Buy if +DI > -DI
        # Sell if -DI > +DI
        
        if current['adx'] > self.threshold:
            if current['plus_di'] > current['minus_di']:
                return 'BUY'
            if current['minus_di'] > current['plus_di']:
                return 'SELL'
                
        return 'HOLD'
