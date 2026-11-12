import os
import argparse
import json
from src.smart_api_client import SmartAPIClient
from src.backtester import Backtester
from src.live_trader import LiveTrader
from src.screener import Screener
from src.logger import SystemLogger

# Import Strategies
from src.strategies import (
    MomentumStrategy, 
    SupertrendStrategy, 
    GoldenCrossStrategy, 
    BollingerSqueezeStrategy,
    IndexDirectionalStrategy
)

STRATEGY_MAP = {
    'momentum': MomentumStrategy,
    'supertrend': SupertrendStrategy,
    'goldencross': GoldenCrossStrategy,
    'bollinger': BollingerSqueezeStrategy,
    'fno_directional': IndexDirectionalStrategy
}

def load_config(path="config.json"):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}

def main():
    parser = argparse.ArgumentParser(description="SmartAPI Trading System")
    parser.add_argument('--mode', choices=['backtest', 'live', 'screener'], default='live', help='Mode: backtest, live, or screener')
    parser.add_argument('--strategy', choices=STRATEGY_MAP.keys(), default='momentum', help='Strategy to run')
    parser.add_argument('--token', default='3045', help='Symbol Token (default: 3045 for SBIN)')
    parser.add_argument('--symbol', default='SBIN-EQ', help='Trading Symbol (default: SBIN-EQ)')
    parser.add_argument('--interval', default='FIVE_MINUTE', help='Candle Interval')
    parser.add_argument('--capital', type=float, default=100000, help='Total Capital')
    parser.add_argument('--websocket', action='store_true', help='Use WebSocket for real-time tick-by-tick data')
    parser.add_argument('--screener', action='store_true', help='Run stock screener for 3-5% 2-3 day move candidates')
    parser.add_argument('--screener-config', default='config/screener_config.json', help='Path to screener config file')
    
    args = parser.parse_args()

    config = load_config()
    credentials = config.get("credentials", {})
    
    api_key = credentials.get("api_key")
    client_code = credentials.get("client_code")
    secret_key = credentials.get("secret_key")
    
    if not all([api_key, client_code, secret_key]):
        print("Error: Missing credentials in config.json")
        return

    # Initialize Client
    client = SmartAPIClient(api_key, client_code, secret_key)
    
    # Authenticate via Browser
    if not client.login_via_browser():
        print("Login failed via Browser.")
        return

    if args.mode == 'screener' or args.screener:
        screener = Screener(api_client=client, config_path=args.screener_config)
        screener.run()
        return

    # Initialize Strategy
    strategy_class = STRATEGY_MAP[args.strategy]
    print(f"Initializing Strategy: {args.strategy}")
    strategy = strategy_class()
    
    if args.mode == 'backtest':
        print(f"Starting Backtest for {args.symbol} ({args.token})")
        # Fixed dates for testing
        backtester = Backtester(
            client, 
            strategy, 
            token=args.token, 
            interval=args.interval, # Use CLI arg
            from_date="2024-01-01 09:15", 
            to_date="2024-01-10 15:30"
        )
        backtester.run()
        
    elif args.mode == 'live':
        trader = LiveTrader(
            api_client=client, 
            strategy=strategy, 
            symbol=args.symbol,
            token=args.token, 
            strategy_name=args.strategy,
            interval=args.interval,
            total_capital=args.capital,
            use_websocket=args.websocket
        )
        trader.start()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Critical Error: {e}")
        SystemLogger.log_error(e, "main_execution")
