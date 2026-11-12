import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.screener import Screener, Candidate

class DummyAPIClient:
    pass

class TestScreener(unittest.TestCase):
    def setUp(self):
        self.api_client = DummyAPIClient()
        self.screener = Screener(api_client=self.api_client)
        self.screener.config['min_daily_volume'] = 1000

    def generate_synthetic_5min_data(self, base_price=100.0, num_days=5, volatility=0.01):
        """
        Generates synthetic 5-minute candle data over multiple trading days.
        Each trading day has 75 bars (9:15 to 15:30).
        """
        records = []
        current_time = datetime.now() - timedelta(days=num_days)
        price = base_price

        for day in range(num_days):
            # Skip weekends
            day_time = current_time + timedelta(days=day)
            if day_time.weekday() >= 5:
                continue

            bar_time = day_time.replace(hour=9, minute=15, second=0, microsecond=0)
            for bar in range(75):
                ret = np.random.normal(0.0005, volatility)
                open_p = price
                close_p = price * (1 + ret)
                high_p = max(open_p, close_p) * (1 + abs(np.random.normal(0, volatility * 0.5)))
                low_p = min(open_p, close_p) * (1 - abs(np.random.normal(0, volatility * 0.5)))
                volume = np.random.randint(1000, 5000)

                records.append({
                    'timestamp': bar_time.strftime("%Y-%m-%d %H:%M:%S"),
                    'open': round(open_p, 2),
                    'high': round(high_p, 2),
                    'low': round(low_p, 2),
                    'close': round(close_p, 2),
                    'volume': volume
                })
                price = close_p
                bar_time += timedelta(minutes=5)

        return pd.DataFrame(records)

    def test_calculate_metrics_valid(self):
        df = self.generate_synthetic_5min_data(base_price=500.0, num_days=5, volatility=0.008)
        candidate = self.screener.calculate_metrics("TEST_STOCK", "1234", df)

        self.assertIsNotNone(candidate)
        self.assertIsInstance(candidate, Candidate)
        self.assertEqual(candidate.symbol, "TEST_STOCK")
        self.assertEqual(candidate.token, "1234")
        self.assertGreater(candidate.latest_price, 0)
        self.assertGreater(candidate.adr_pct, 0)
        self.assertGreater(candidate.move_potential_2d_pct, 0)
        self.assertIn(candidate.signal_direction, ["BULLISH", "BEARISH", "NEUTRAL"])
        self.assertGreaterEqual(candidate.probability_score, 0)
        self.assertLessEqual(candidate.probability_score, 100)

    def test_calculate_metrics_low_volume_filtered(self):
        df = self.generate_synthetic_5min_data(base_price=100.0, num_days=3, volatility=0.005)
        df['volume'] = 10  # Extremely low volume
        candidate = self.screener.calculate_metrics("LOW_VOL", "9999", df)

        self.assertIsNone(candidate)

    def test_calculate_metrics_empty_df(self):
        df = pd.DataFrame()
        candidate = self.screener.calculate_metrics("EMPTY", "0000", df)
        self.assertIsNone(candidate)

if __name__ == '__main__':
    unittest.main()
