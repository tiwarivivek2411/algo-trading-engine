import os
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from .smart_api_client import SmartAPIClient
from .logger import SystemLogger

@dataclass
class Candidate:
    symbol: str
    token: str
    latest_price: float
    adr_pct: float                # Average Daily Range %
    atr_5m: float                 # 5-minute Average True Range
    atr_5m_pct: float             # 5-minute ATR as % of price
    move_potential_2d_pct: float  # Estimated 2-3 day potential move %
    volatility_std_pct: float     # Scaled 2-3 day standard deviation %
    avg_daily_volume: float
    probability_score: float      # Composite probability score (0-100)
    signal_direction: str         # BULLISH, BEARISH, or NEUTRAL

class Screener:
    def __init__(self, api_client: SmartAPIClient, config_path: str = "config/screener_config.json"):
        self.api_client = api_client
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> dict:
        default_config = {
            "symbol_file": "nifty50_tokens.json",
            "interval": "FIVE_MINUTE",
            "lookback_days": 10,
            "min_potential_move_pct": 3.0,
            "max_potential_move_pct": 10.0,
            "min_daily_volume": 50000,
            "output_file": "data/screener_results.csv"
        }
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    loaded = json.load(f)
                    default_config.update(loaded)
            except Exception as e:
                print(f"Warning: Could not parse config at {self.config_path}, using defaults. Error: {e}")
        return default_config

    def load_symbols(self) -> Dict[str, str]:
        symbol_file = self.config.get("symbol_file", "nifty50_tokens.json")
        if not os.path.exists(symbol_file):
            print(f"Error: Symbol file {symbol_file} not found.")
            return {}
        try:
            with open(symbol_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading symbol file {symbol_file}: {e}")
            return {}

    def calculate_metrics(self, symbol: str, token: str, df: pd.DataFrame) -> Optional[Candidate]:
        """
        Calculates volatility, ATR, volume, and probability metrics from 5-minute candle data.
        """
        if df.empty or len(df) < 50:
            return None

        df = df.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)

        latest_price = float(df['close'].iloc[-1])
        if latest_price <= 0:
            return None

        # 1. 5-Minute True Range & ATR (14-period)
        high_low = df['high'] - df['low']
        high_close_prev = (df['high'] - df['close'].shift(1)).abs()
        low_close_prev = (df['low'] - df['close'].shift(1)).abs()
        tr_5m = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
        atr_5m = tr_5m.rolling(window=14, min_periods=1).mean().iloc[-1]
        atr_5m_pct = (atr_5m / latest_price) * 100.0

        # 2. Daily aggregation for Average Daily Range (ADR)
        df['date'] = df['timestamp'].dt.date
        daily_df = df.groupby('date').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).reset_index()

        if len(daily_df) < 2:
            return None

        daily_df['range_pct'] = ((daily_df['high'] - daily_df['low']) / daily_df['open']) * 100.0
        adr_pct = daily_df['range_pct'].mean()
        avg_daily_volume = daily_df['volume'].mean()

        if avg_daily_volume < self.config.get("min_daily_volume", 50000):
            return None

        # 3. 5-Minute Log Return Volatility
        returns_5m = np.log(df['close'] / df['close'].shift(1)).dropna()
        std_5m = returns_5m.std()
        
        # 1 trading day = 75 five-minute bars (375 mins / 5)
        # 2.5 trading days = 187.5 five-minute bars
        bars_2_5d = 187.5
        volatility_std_pct = (std_5m * np.sqrt(bars_2_5d)) * 100.0

        # 4. Projected 2-3 Day Potential Move %
        # Blend of ADR projected over 2.5 days (ADR * sqrt(2.5)) and 2.5-day 2-sigma return potential
        adr_projected_2d = adr_pct * np.sqrt(2.5)
        move_potential_2d_pct = round((0.5 * adr_projected_2d) + (0.5 * (volatility_std_pct * 1.5)), 2)

        # 5. Technical Trend & Momentum for Probability Scoring
        # EMA 20 & 50 on 5-min
        df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
        
        # RSI 14
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-9)
        rsi = 100 - (100 / (1 + rs))
        latest_rsi = rsi.iloc[-1] if not rsi.empty else 50.0

        ema20_curr = df['ema20'].iloc[-1]
        ema50_curr = df['ema50'].iloc[-1]

        signal_direction = "NEUTRAL"
        trend_score = 50.0

        if latest_price > ema20_curr > ema50_curr:
            signal_direction = "BULLISH"
            trend_score += 25.0
            if 50.0 <= latest_rsi <= 70.0:
                trend_score += 15.0
        elif latest_price < ema20_curr < ema50_curr:
            signal_direction = "BEARISH"
            trend_score += 25.0
            if 30.0 <= latest_rsi <= 50.0:
                trend_score += 15.0

        # Volatility match score: reward stocks whose projected move is right in the 3-5% target window
        min_target = self.config.get("min_potential_move_pct", 3.0)
        max_target = self.config.get("max_potential_move_pct", 10.0)

        vol_score = 0.0
        if min_target <= move_potential_2d_pct <= max_target:
            vol_score = 100.0 - abs(move_potential_2d_pct - 4.0) * 10.0
            vol_score = max(50.0, min(100.0, vol_score))

        probability_score = round((0.6 * trend_score) + (0.4 * vol_score), 2)

        return Candidate(
            symbol=symbol,
            token=token,
            latest_price=round(latest_price, 2),
            adr_pct=round(adr_pct, 2),
            atr_5m=round(atr_5m, 2),
            atr_5m_pct=round(atr_5m_pct, 2),
            move_potential_2d_pct=move_potential_2d_pct,
            volatility_std_pct=round(volatility_std_pct, 2),
            avg_daily_volume=round(avg_daily_volume, 0),
            probability_score=probability_score,
            signal_direction=signal_direction
        )

    def run(self) -> List[Candidate]:
        """
        Executes the stock screening process across all configured tokens.
        """
        symbol_map = self.load_symbols()
        if not symbol_map:
            print("No symbols loaded. Aborting screening.")
            return []

        lookback_days = self.config.get("lookback_days", 10)
        interval = self.config.get("interval", "FIVE_MINUTE")
        min_move = self.config.get("min_potential_move_pct", 3.0)
        max_move = self.config.get("max_potential_move_pct", 10.0)

        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=lookback_days)
        from_date = start_dt.strftime("%Y-%m-%d %H:%M")
        to_date = end_dt.strftime("%Y-%m-%d %H:%M")

        print(f"\n--- Starting 5-Min Multi-Stock Screener ---")
        print(f"Scanning {len(symbol_map)} symbols from {from_date} to {to_date}...")
        print(f"Targeting 2-3 Day Potential Move: {min_move}% - {max_move}%\n")

        candidates: List[Candidate] = []

        for symbol, token in symbol_map.items():
            try:
                df = self.api_client.fetch_historical_data(
                    token=str(token),
                    interval=interval,
                    from_date=from_date,
                    to_date=to_date
                )
                if df.empty:
                    continue

                candidate = self.calculate_metrics(symbol, str(token), df)
                if candidate and (min_move <= candidate.move_potential_2d_pct <= max_move):
                    candidates.append(candidate)
            except Exception as e:
                print(f"Error screening {symbol} ({token}): {e}")
                SystemLogger.log_error(e, f"screener_{symbol}")

        # Sort by probability score descending
        candidates.sort(key=lambda c: c.probability_score, reverse=True)

        self._output_results(candidates)
        return candidates

    def _output_results(self, candidates: List[Candidate]):
        output_file = self.config.get("output_file", "data/screener_results.csv")
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        if not candidates:
            print("No candidates met the screening criteria.")
            return

        df_out = pd.DataFrame([asdict(c) for c in candidates])
        df_out.to_csv(output_file, index=False)

        print(f"\n================ SCREENER RESULTS ({len(candidates)} Candidates Found) ================")
        header = f"{'Symbol':<12} | {'Price (₹)':<10} | {'ADR %':<7} | {'2-3D Move %':<12} | {'Direction':<10} | {'Prob Score':<10}"
        print(header)
        print("-" * len(header))
        for c in candidates:
            row = f"{c.symbol:<12} | {c.latest_price:<10.2f} | {c.adr_pct:<7.2f} | {c.move_potential_2d_pct:<12.2f} | {c.signal_direction:<10} | {c.probability_score:<10.2f}"
            print(row)
        print("-" * len(header))
        print(f"\nResults saved to: {output_file}\n")
