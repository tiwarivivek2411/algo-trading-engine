import sys
import os
import json
import pandas as pd
from datetime import datetime

sys.path.append(os.getcwd())
from src.smart_api_client import SmartAPIClient
from src.backtester import Backtester
from src.strategy_factory import StrategyFactory

# Configuration
with open('config.json', 'r') as f:
    config = json.load(f)

client = SmartAPIClient(
    config['credentials']['api_key'], 
    config['credentials']['client_code'], 
    config['credentials']['secret_key']
)
client._load_tokens()

# Test matrix definitions
SYMBOLS = {
    "NIFTY50": {"spot": "99926000", "future": "NIFTY-FUT"}, # Future token would be needed here
    "BANKNIFTY": {"spot": "99926009", "future": "BANKNIFTY-FUT"},
    "SBIN": {"spot": "3045", "future": "SBIN-FUT"},
    "RELIANCE": {"spot": "2885", "future": "RELIANCE-FUT"}
}

# Tokens for futures (Placeholder for now, in real life we'd look them up)
FUT_TOKENS = {
    "NIFTY-FUT": "12345", # Placeholder
    "BANKNIFTY-FUT": "67890",
    "SBIN-FUT": "999",
    "RELIANCE-FUT": "888"
}

INTERVAL = 'FIVE_MINUTE'
FROM_DATE = '2024-01-01 09:15'
TO_DATE = '2025-01-01 15:30'

def main():
    strategies = StrategyFactory.generate_strategies()
    all_results = []
    
    os.makedirs("backtest_reports/universal", exist_ok=True)
    
    for sym_name, sym_cfg in SYMBOLS.items():
        print(f"--- Processing {sym_name} ---")
        
        # Sources: Spot, Future (if exists)
        sources = [("SPOT", sym_cfg['spot'])]
        # if sym_cfg['future'] in FUT_TOKENS:
        #    sources.append(("FUT", FUT_TOKENS[sym_cfg['future']]))
            
        for source_name, source_token in sources:
            for strat_name, strategy in strategies.items():
                if not strat_name.startswith("U_"): continue # Only run universal ones here
                
                # We can also cross-trade (e.g. signal on spot, trade on spot - which handles Bees/Eq/Options)
                # The strategy.mode determines if it's OPTION or EQUITY.
                
                try:
                    bt = Backtester(client, strategy, source_token, INTERVAL, FROM_DATE, TO_DATE, silent=True)
                    res = bt.run()
                    
                    if res['trades']:
                        summary = {
                            "Symbol": sym_name,
                            "Source": source_name,
                            "Strategy": strat_name,
                            "Return": round(res['total_return'], 2),
                            "Trades": len(res['trades']),
                            "WinRate": round(sum(1 for t in res['trades'] if t.get('pnl', 0) > 0) / len(res['trades']) * 100, 2)
                        }
                        all_results.append(summary)
                        print(f"[OK] {strat_name} on {source_name}: {summary['Return']}")
                except Exception as e:
                    print(f"[ERR] {strat_name} on {sym_name}: {e}")

    # Generate master report
    df = pd.DataFrame(all_results)
    df.to_csv("backtest_reports/universal_summary.csv", index=False)
    print("\nUniversal Backtest Completed. Summary saved to backtest_reports/universal_summary.csv")

if __name__ == "__main__":
    main()
