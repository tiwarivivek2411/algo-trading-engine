import argparse
import json
import os
import sys
import pandas as pd
from datetime import datetime, timedelta

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.smart_api_client import SmartAPIClient
from src.backtester import Backtester
from src.strategy_factory import StrategyFactory

# Generate 50+ Strategies
STRATEGIES = StrategyFactory.generate_strategies()

TIMEFRAMES = {
    '1Y': 365,
}

def load_config(path="config.json"):
    with open(path, 'r') as f:
        return json.load(f)

def load_tokens(path="nifty50_tokens.json"):
    with open(path, 'r') as f:
        return json.load(f)

def run_bulk_backtest():
    config = load_config()
    creds = config.get("credentials", {})
    
    # Initialize Client
    client = SmartAPIClient(creds["api_key"], creds["client_code"], creds["secret_key"])
    if not client._load_tokens():
        print("Please login manually via main.py first to generate tokens.json")
        return

    tokens_map = load_tokens()
    all_results = []
    
    # User requested to replace/overwrite. Using a fixed directory.
    report_dir = "backtest_reports"
    
    # REMOVED CLEANUP LOGIC TO ALLOW RESUME
    if not os.path.exists(report_dir):
        os.makedirs(report_dir)
        
    master_summary_file = os.path.join(report_dir, f"master_summary.csv")
    print(f"Starting Bulk Backtest (50+ Strategies). Reports will be saved to {report_dir}/")
    
    total_iterations = len(tokens_map) * len(STRATEGIES) * len(TIMEFRAMES)
    progress = 0
    
    for symbol, token in tokens_map.items():
        # Create Symbol Directory
        symbol_dir = os.path.join(report_dir, symbol)
        if not os.path.exists(symbol_dir):
            os.makedirs(symbol_dir)

        for strat_name, strat_class in STRATEGIES.items():
            for tf_name, days in TIMEFRAMES.items():
                progress += 1
                
                # Check if Report Exists
                detail_file = os.path.join(symbol_dir, f"{strat_name}_{tf_name}.csv")
                
                # Determine Interval
                if strat_name in ['goldencross', 'bollinger']:
                    interval = "ONE_DAY"
                else:
                    interval = "FIVE_MINUTE"

                if os.path.exists(detail_file):
                    print(f"[{progress}/{total_iterations}] Skipping {symbol} | {strat_name} (Report Exists)")
                    
                    # Reconstruct Stats for Master Summary
                    try:
                        existing_df = pd.read_csv(detail_file)
                        trade_count = len(existing_df)
                        if 'pnl' in existing_df.columns and not existing_df.empty:
                            total_return = existing_df['pnl'].sum()
                            # Approximate win rate check
                            wins = len(existing_df[existing_df['pnl'] > 0])
                            # Assumption: Trade execution count in summary was total rows / 2 approx?
                            # Or just rows. Let's use rows for consistency with live run.
                            win_rate = (wins / (trade_count / 2)) * 100 if trade_count > 0 else 0 
                        else:
                            total_return = 0.0
                            win_rate = 0.0

                        all_results.append({
                            "Symbol": symbol,
                            "Token": token,
                            "Strategy": strat_name,
                            "Timeframe": tf_name,
                            "Interval": interval,
                            "Total Return": round(total_return, 2),
                            "Trade Execution Count": trade_count,
                            "Win Rate %": round(win_rate, 2),
                            "Report Path": f"{symbol}/{strat_name}_{tf_name}.csv"
                        })
                    except Exception as e:
                        print(f"Failed to read existing report {detail_file}: {e}")
                    
                    continue # SKIP EXECUTION

                print(f"[{progress}/{total_iterations}] Testing {symbol} | {strat_name} | {tf_name}")
                
                # Setup Dates
                to_date_obj = datetime.now()
                from_date_obj = to_date_obj - timedelta(days=days)
                
                from_date = from_date_obj.strftime("%Y-%m-%d 09:15")
                to_date = to_date_obj.strftime("%Y-%m-%d 15:30")
                
                try:
                    # Rate Limit Handling: Angel One has limits (~3 req/sec for data)
                    import time
                    time.sleep(1.1) 
                    
                    # Factory returns instances, but Backtester modifies state?
                    # Ideally we should clone it or reset it.
                    # Current Strategy classes have `self.data_buffer` which needs reset.
                    # Quick fix: manually reset data buffer
                    strategy = strat_class # It is already an instance from the dict
                    if hasattr(strategy, 'data_buffer'):
                        strategy.data_buffer = pd.DataFrame()
                        
                    backtester = Backtester(
                        client, 
                        strategy, 
                        token, 
                        interval, 
                        from_date, 
                        to_date, 
                        silent=True
                    )
                    
                    res = backtester.run()
                    trades = res.get('trades', [])
                    trade_count = len(trades)
                    total_return = res.get('total_return', 0.0)
                    
                    # --- Detailed Reporting Logic ---
                    if trades:
                        trades_df = pd.DataFrame(trades)
                        # Add PnL if missing (for buy/sell rows it might be NaN)
                        if 'pnl' not in trades_df.columns:
                            trades_df['pnl'] = 0.0
                        
                        trades_df['pnl'] = trades_df['pnl'].fillna(0.0)
                        trades_df['cumulative_pnl'] = trades_df['pnl'].cumsum()
                        
                        # Save Detailed Report
                        trades_df.to_csv(detail_file, index=False)
                    # -------------------------------

                    # Calculate Win Rate
                    wins = len([t for t in trades if t.get('pnl', 0) > 0])
                    win_rate = (wins / (trade_count / 2)) * 100 if trade_count > 0 else 0 
                    
                    all_results.append({
                        "Symbol": symbol,
                        "Token": token,
                        "Strategy": strat_name,
                        "Timeframe": tf_name,
                        "Interval": interval,
                        "Total Return": round(total_return, 2),
                        "Trade Execution Count": trade_count,
                        "Win Rate %": round(win_rate, 2),
                        "Report Path": f"{symbol}/{strat_name}_{tf_name}.csv"
                    })
                    
                except Exception as e:
                    print(f"Error testing {symbol} {strat_name}: {e}")
                    all_results.append({
                        "Symbol": symbol,
                        "Strategy": strat_name,
                        "Timeframe": tf_name,
                        "Error": str(e)
                    })
        
        # Intermediate Save of Master Summary
        pd.DataFrame(all_results).to_csv(master_summary_file, index=False)

    # Final Save
    df = pd.DataFrame(all_results)
    df.to_csv(master_summary_file, index=False)
    print(f"\nBulk Backtest Completed. Full reports in {report_dir}/")
    print(df.sort_values(by="Total Return", ascending=False).head(10))

if __name__ == "__main__":
    run_bulk_backtest()
