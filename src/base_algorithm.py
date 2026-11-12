import pandas as pd
from abc import ABC, abstractmethod

class BaseAlgorithm(ABC):
    """
    Interface for core price-action algorithms.
    These algos do NOT know about options or equity execution. 
    They only know OHLC data and directional bias.
    """
    @abstractmethod
    def on_data(self, candle_data: pd.Series):
        """Processes a single candle."""
        pass

    @abstractmethod
    def generate_bias(self) -> str:
        """Returns 'BULLISH', 'BEARISH', or 'HOLD'."""
        pass
