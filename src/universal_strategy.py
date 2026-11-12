import pandas as pd
from src.strategy_interface import Strategy
from src.base_algorithm import BaseAlgorithm

class UniversalStrategy(Strategy):
    """
    Glue between a Directional Algotrithm and the Execution Engine.
    Maps BULLISH/BEARISH signals to BUY/SELL/COVER based on the mode.
    """
    def __init__(self, base_algo: BaseAlgorithm, mode: str, strike_offset="ATM"):
        """
        mode: 
        - 'EQUITY_INTRADAY': Buy/Sell on current symbol. Square off daily.
        - 'EQUITY_POSITIONAL': Buy/Sell on current symbol. 
        - 'OPTION_BUY': Buy Call for Bullish, Buy Put for Bearish.
        - 'OPTION_SELL': Sell Put for Bullish, Sell Call for Bearish.
        """
        self.base_algo = base_algo
        self.mode = mode
        self.strike_offset = strike_offset
        # Backtester looks for these
        self.instrument = 'OPT' if 'OPTION' in mode else 'EQUITY'
        
    def on_tick(self, tick_data):
        pass

    def on_data(self, candle_data):
        self.base_algo.on_data(candle_data)

    def generate_signal(self):
        bias = self.base_algo.generate_bias()
        
        if bias == 'HOLD':
            return 'HOLD'
            
        if self.mode.startswith('EQUITY'):
            if bias == 'BULLISH': return 'BUY'
            if bias == 'BEARISH': return 'SELL'
            
        if self.mode == 'OPTION_BUY':
            return {
                'action': 'BUY',
                'asset': 'OPTION',
                'type': 'CE' if bias == 'BULLISH' else 'PE',
                'strike_offset': self.strike_offset
            }
            
        if self.mode == 'OPTION_SELL':
            # Option Selling: Bullish bias -> Sell Put (Profit if price stays up/range)
            # Bearish bias -> Sell Call
            return {
                'action': 'SELL',
                'asset': 'OPTION',
                'type': 'PE' if bias == 'BULLISH' else 'CE',
                'strike_offset': self.strike_offset
            }
            
        return 'HOLD'
