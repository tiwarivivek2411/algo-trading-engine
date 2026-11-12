from abc import ABC, abstractmethod

class Strategy(ABC):
    """
    Abstract Base Class for trading strategies.
    """

    @abstractmethod
    def on_tick(self, tick_data):
        """
        Called when new real-time tick data is received.
        :param tick_data: Dictionary containing tick info (price, volume, etc.)
        """
        pass

    @abstractmethod
    def on_data(self, candle_data):
        """
        Called when new historical/candle data is received (e.g., for backtesting or bar close).
        :param candle_data: DataFrame or Dict containing candle info.
        """
        pass

    @abstractmethod
    def generate_signal(self):
        """
        Logic to determine if a trade should be executed.
        :return: 'BUY', 'SELL', or 'HOLD', along with optional metadata (e.g., price, stoploss).
        """
        pass
