import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
from src.smart_api_client import SmartAPIClient
from src.backtester import Backtester
from src.live_trader import LiveTrader
from src.strategy_interface import Strategy

class MockStrategy(Strategy):
    def on_tick(self, tick_data):
        pass
    def on_data(self, candle_data):
        pass
    def generate_signal(self):
        return 'BUY'

class TestE2E(unittest.TestCase):
    def setUp(self):
        self.mock_api = MagicMock(spec=SmartAPIClient)
        self.strategy = MockStrategy()
        
    def test_backtester_flow(self):
        """
        Test that backtester correctly iterates mocks and calculates P&L.
        """
        # Mock Historical Data
        data = {
            'timestamp': [pd.Timestamp('2024-01-01'), pd.Timestamp('2024-01-02')],
            'open': [100, 105],
            'high': [110, 115],
            'low': [95, 100],
            'close': [105, 110], # Buy at 105, hold till end? Logic depends on strategy
            'volume': [1000, 1200]
        }
        df = pd.DataFrame(data)
        self.mock_api.fetch_historical_data.return_value = df
        
        # Run Backtester
        backtester = Backtester(self.mock_api, self.strategy, "TOKEN", "ONE_DAY", "2024-01-01", "2024-01-02")
        results = backtester.run()
        
        # Verify API called
        self.mock_api.fetch_historical_data.assert_called_once()
        
        # Verify Strategy interaction (signals generated)
        # In our MockStrategy, it always BUYS.
        # So it should Buy at 105. At 110 (next row), it's already Long.
        # It never sells. So Trades: [BUY @ 105]. Net return 0 (unrealized not counted in simple implementation yet)
        self.assertEqual(len(results['trades']), 1) 
        self.assertEqual(results['trades'][0]['type'], 'BUY')
        self.assertEqual(results['trades'][0]['price'], 105)

    @patch('time.sleep', return_value=None) # Mock sleep to speed up
    @patch('src.live_trader.RiskManager')
    def test_live_trader_flow(self, mock_risk_manager_cls, mock_sleep):
        """
        Test that LiveTrader calls API based on signal and risk.
        """
        # Setup Mock Risk Manager
        mock_rm = mock_risk_manager_cls.return_value
        mock_rm.calculate_quantity.return_value = 10
        mock_rm.calculate_stoploss.return_value = 90.0

        # Mock Historical Data (for loop)
        data = pd.DataFrame({'close': [100.0]})
        self.mock_api.fetch_historical_data.return_value = data
        self.mock_api.session_data = {'status': True} # Already logged in

        # Run LiveTrader - one iteration hack
        trader = LiveTrader(self.mock_api, self.strategy, "TOKEN")
        
        # Override start to run only once loop logic (extract logic to method ideally, but for now mocking running state)
        # Or we can just test the inner logic? 
        # Ideally refactor `start` to `tick`, but for E2E we want to test the loop structure or break it.
        # Let's start and have it throw exception after 1 loop to break? or set is_running False via side_effect?
        
        def side_effect(*args, **kwargs):
            trader.is_running = False # Stop after first call
            return data
            
        self.mock_api.fetch_historical_data.side_effect = side_effect
        
        trader.start()
        
        # Verify calls
        self.mock_api.fetch_historical_data.assert_called()
        self.mock_api.place_order.assert_called_once()
        
        # Check args passed to place_order
        args, kwargs = self.mock_api.place_order.call_args
        self.assertEqual(kwargs['quantity'], 10)
        self.assertEqual(kwargs['stoploss'], 90.0)
        self.assertEqual(kwargs['transaction_type'], 'BUY')

if __name__ == '__main__':
    unittest.main()
