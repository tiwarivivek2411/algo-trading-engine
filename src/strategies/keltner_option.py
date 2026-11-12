import pandas as pd
from src.strategy_interface import Strategy

class KeltnerOptionStrategy(Strategy):
    def __init__(self, ema_period=10, atr_period=10, multiplier=2.0, signal_source="SPOT", strike_offset="ATM", trade_mode="LONG_ONLY"):
        """
        Keltner Strategy specifically for Options.
        signal_source: "SPOT" (e.g. NIFTY 50) or "OPTION" (the option price data itself).
        strike_offset: "ATM", "OTM1", "OTM2", "ITM1", etc.
        trade_mode: "LONG_ONLY" (Buy Call for Up, Buy Put for Down), "SHORT_ONLY", or "REVERSE".
        """
        self.ema_period = ema_period
        self.atr_period = atr_period
        self.multiplier = multiplier
        self.signal_source = signal_source
        self.strike_offset = strike_offset
        self.trade_mode = trade_mode
        self.instrument = 'OPT' # Crucial for Backtester
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
        if len(self.data_buffer) < max(self.ema_period, self.atr_period) + 2:
            return 'HOLD'

        df = self.data_buffer.copy()
        
        # 1. Calculate Keltner Channels
        # EMA
        df['ema'] = df['close'].ewm(span=self.ema_period, adjust=False).mean()
        
        # ATR
        high, low, close = df['high'], df['low'], df['close']
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
        
        # 2. Determine Directional Bias based on Keltner Breakout
        raw_bias = 'HOLD'
        if prev['close'] <= prev['upper'] and current['close'] > current['upper']:
            raw_bias = 'BULLISH'
        elif prev['close'] >= prev['lower'] and current['close'] < current['lower']:
            raw_bias = 'BEARISH'
        
        if raw_bias == 'HOLD':
            return 'HOLD'

        # 3. Handle Option Specific Signal Logic
        # Result needs to be a rich signal compatible with Backtester's option logic:
        # e.g., {'action': 'BUY', 'asset': 'OPTION', 'type': 'CE', 'strike_offset': 'ATM'}
        
        if self.signal_source == "OPTION":
            # If we are analyzing the option itself, Bullish = BUY, Bearish = SELL/EXIT
            if raw_bias == 'BULLISH': return 'BUY'
            if raw_bias == 'BEARISH': return 'SELL'
            return 'HOLD'

        # If signal_source is "SPOT", we need to translate Bullish/Bearish to Option types
        signal_obj = {
            'action': 'HOLD',
            'asset': 'OPTION',
            'strike_offset': self.strike_offset
        }

        if raw_bias == 'BULLISH':
            # Buy Call
            signal_obj['action'] = 'BUY'
            signal_obj['type'] = 'CE'
        elif raw_bias == 'BEARISH':
            # Buy Put
            signal_obj['action'] = 'BUY'
            signal_obj['type'] = 'PE'

        return signal_obj
