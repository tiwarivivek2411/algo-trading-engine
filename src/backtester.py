import pandas as pd
from .smart_api_client import SmartAPIClient

class Backtester:
    def __init__(self, api_client: SmartAPIClient, strategy, token, interval, from_date, to_date, trade_token=None, silent=False):
        self.api_client = api_client
        self.strategy = strategy
        self.signal_token = token
        self.trade_token = trade_token if trade_token else token
        self.interval = interval
        self.from_date = from_date
        self.to_date = to_date
        self.silent = silent
        self.results = {
            "total_return": 0.0,
            "trades": []
        }

    def run(self):
        """
        Executes the backtest.
        """
        if not self.silent:
            print(f"Starting backtest. Signal: {self.signal_token}, Trade: {self.trade_token}...")
        
        # 1. Fetch Data
        signal_data = self.api_client.fetch_historical_data(
            self.signal_token, self.interval, self.from_date, self.to_date
        )
        
        if signal_data.empty:
            if not self.silent: print("No signal data fetched.")
            return self.results

        if self.trade_token != self.signal_token:
            trade_data = self.api_client.fetch_historical_data(
                self.trade_token, self.interval, self.from_date, self.to_date
            )
            if trade_data.empty:
                if not self.silent: print("No trade data fetched.")
                return self.results
            # Align data
            data = pd.merge(signal_data, trade_data, on='timestamp', suffixes=('_sig', '_trd'), how='inner')
        else:
            # Single token mode
            data = signal_data.copy()
            for col in ['open', 'high', 'low', 'close', 'volume']:
                data[f'{col}_sig'] = data[col]
                data[f'{col}_trd'] = data[col]

        if not self.silent:
            print(f"Aligned {len(data)} candles.")

        # 2. Iterate and feed to strategy
        position = 0 # 1 for Long, -1 for Short, 0 for Flat
        entry_price = 0.0
        entry_qty = 0
        entry_strike = 0
        
        # Import utils
        from .options_utils import calculate_option_delta, simulate_option_pnl, get_lot_size, get_strike_step, get_atm_strike

        for index, row in data.iterrows():
            # Pass signal data to strategy
            sig_candle = {
                'timestamp': row['timestamp'],
                'open': row['open_sig'],
                'high': row['high_sig'],
                'low': row['low_sig'],
                'close': row['close_sig'],
                'volume': row['volume_sig']
            }
            self.strategy.on_data(sig_candle)
            
            # Get signal
            signal = self.strategy.generate_signal()
            
            # Simple execution logic (Market Orders assumed)
            current_spot_price = row['close_sig']
            trade_price = row['close_trd']
            
            # Format timestamp for loop
            timestamp = row['timestamp']
            date_str = timestamp.strftime('%d-%m-%Y')
            time_str = timestamp.strftime('%H:%M')
            formatted_time = f"{date_str} {time_str}"
            
            # Determine Instrument Type and Timeframe
            is_option = getattr(self.strategy, 'instrument', 'EQUITY') == 'OPT'
            is_intraday = self.interval in ['ONE_MINUTE', 'THREE_MINUTE', 'FIVE_MINUTE', 'FIFTEEN_MINUTE', 'THIRTY_MINUTE', 'ONE_HOUR']
            
            # Capital Settings
            CAPITAL = 20000.0
            LEVERAGE = 5.0 if is_intraday else 1.0
            
            # Adjust trade price for NiftyBees if signal is Nifty Spot
            is_nifty_equity = (str(self.trade_token) == "99926000" and not is_option)
            if is_nifty_equity:
                trade_price = trade_price / 100.0
            
            # Calculate Quantity
            qty = 1
            if is_option:
                # Lot sizes for options (often tied to the signal index like NIFTY)
                qty = get_lot_size(self.signal_token)
            else:
                # Equity / NiftyBees
                buying_power = CAPITAL * LEVERAGE
                if trade_price > 0:
                    qty = int(buying_power / trade_price)
            
            # --- AUTO SQUARE OFF & EXPIRY CHECK ---
            current_time_minutes = timestamp.hour * 60 + timestamp.minute
            cutoff_time_minutes = 15 * 60 + 15 # 15:15
            is_thursday = (timestamp.weekday() == 3) # 0=Mon, 3=Thu
            
            should_square_off = False
            note = ""
            
            if current_time_minutes >= cutoff_time_minutes:
                # Rule 1: Equity Intraday (5x margin) -> Must Close Daily
                if is_intraday and not is_option and position != 0:
                    should_square_off = True
                    note = "AutoSquareOff_Intraday"
                    
                # Rule 2: Option Expiry (Thursdays) -> Must Close Weekly Series
                if is_option and is_thursday and position != 0:
                    should_square_off = True
                    note = "AutoSquareOff_Expiry"

            if should_square_off:
                if is_option:
                    opt_type = signal_type_override or getattr(self.strategy, 'type', 'CE')
                    pnl, _ = simulate_option_pnl(entry_price, current_spot_price, entry_strike, opt_type, entry_qty)
                    invested_capital = entry_price * entry_qty
                    if position == -1: pnl = -pnl
                    asset_lbl = f"OPT_{entry_strike}_{opt_type}"
                else:
                    pnl = (trade_price - entry_price) * entry_qty if position == 1 else (entry_price - trade_price) * entry_qty
                    invested_capital = CAPITAL
                    asset_lbl = "TRADE_ASSET"
                
                self.results['total_return'] += pnl
                pnl_percent = (pnl / invested_capital) * 100 if invested_capital > 0 else 0.0
                cum_pnl_percent = (self.results['total_return'] / CAPITAL) * 100
                
                type_lbl = 'SELL' if position == 1 else 'COVER'
                self.results['trades'].append({
                    'type': type_lbl, 
                    'price': trade_price if not is_option else current_spot_price, 
                    'pnl': pnl, 
                    'qty': entry_qty, 
                    'pnl_percent': round(pnl_percent, 2),
                    'cum_pnl_percent': round(cum_pnl_percent, 2),
                    'time': formatted_time,
                    'asset': asset_lbl,
                    'note': note
                })
                position = 0 # Closed
                continue # Skip signal processing for this candle

            # --- SIGNAL PROCESSING ---
            # Support both string signals ('BUY', 'SELL') and rich signals (dict)
            action = signal
            signal_type_override = None
            signal_strike_override = None
            
            if isinstance(signal, dict):
                action = signal.get('action', 'HOLD')
                signal_type_override = signal.get('type')
                signal_strike_override = signal.get('strike_offset')

            if action == 'BUY':
                if position == 0:
                    # OPEN LONG
                    position = 1
                    entry_price = trade_price if not is_option else current_spot_price
                    entry_qty = qty
                    if is_option:
                        opt_type = signal_type_override or getattr(self.strategy, 'type', 'CE')
                        strike_os = signal_strike_override or getattr(self.strategy, 'strike_offset', 'ATM')
                        
                        step = get_strike_step(self.signal_token)
                        atm = get_atm_strike(current_spot_price, step)
                        
                        if strike_os == 'ATM': entry_strike = atm
                        elif strike_os == 'ITM1': entry_strike = atm - step if opt_type == 'CE' else atm + step
                        elif strike_os == 'OTM1': entry_strike = atm + step if opt_type == 'CE' else atm - step
                        else: entry_strike = atm
                        
                        asset_name = f"OPT_{entry_strike}_{opt_type}"
                    else:
                        asset_name = "TRADE_ASSET"
                    self.results['trades'].append({'type': 'BUY', 'price': entry_price, 'qty': qty, 'time': formatted_time, 'asset': asset_name})
                        
                elif position == -1:
                    # CLOSE SHORT (COVER) & REVERSE TO LONG
                    if is_option:
                        opt_type = signal_type_override or getattr(self.strategy, 'type', 'CE')
                        pnl, _ = simulate_option_pnl(entry_price, current_spot_price, entry_strike, opt_type, entry_qty)
                        invested_capital = entry_price * entry_qty
                        pnl = -pnl # Short Option Profit
                        asset_lbl = f"OPT_{entry_strike}_{opt_type}"
                    else:
                        pnl = (entry_price - trade_price) * entry_qty
                        invested_capital = CAPITAL
                        asset_lbl = "TRADE_ASSET"
                        
                    self.results['total_return'] += pnl
                    pnl_percent = (pnl / invested_capital) * 100 if invested_capital > 0 else 0.0
                    cum_pnl_percent = (self.results['total_return'] / CAPITAL) * 100
                        
                    self.results['trades'].append({
                        'type': 'COVER', 'price': trade_price, 'pnl': pnl, 'qty': entry_qty, 
                        'pnl_percent': round(pnl_percent, 2), 'cum_pnl_percent': round(cum_pnl_percent, 2),
                        'time': formatted_time, 'asset': asset_lbl
                    })
                    
                    # New Long
                    position = 1
                    entry_price = trade_price if not is_option else current_spot_price
                    entry_qty = qty
                    if is_option:
                        step = get_strike_step(self.signal_token)
                        entry_strike = get_atm_strike(current_spot_price, step)
                        asset_lbl = f"OPT_{entry_strike}_{getattr(self.strategy, 'type', 'CE')}"
                    self.results['trades'].append({'type': 'BUY', 'price': entry_price, 'qty': qty, 'time': formatted_time, 'asset': asset_lbl})
                    
            elif action == 'SELL':
                if position == 0:
                    # OPEN SHORT
                    position = -1
                    entry_price = trade_price if not is_option else current_spot_price
                    entry_qty = qty
                    if is_option:
                         opt_type = signal_type_override or getattr(self.strategy, 'type', 'CE')
                         strike_os = signal_strike_override or getattr(self.strategy, 'strike_offset', 'ATM')
                         
                         step = get_strike_step(self.signal_token)
                         atm = get_atm_strike(current_spot_price, step)
                         
                         if strike_os == 'ATM': entry_strike = atm
                         elif strike_os == 'ITM1': entry_strike = atm - step if opt_type == 'CE' else atm + step
                         elif strike_os == 'OTM1': entry_strike = atm + step if opt_type == 'CE' else atm - step
                         else: entry_strike = atm
                         
                         asset_lbl = f"OPT_{entry_strike}_{opt_type}"
                    else:
                        asset_lbl = "TRADE_ASSET"
                    self.results['trades'].append({'type': 'SELL', 'price': entry_price, 'qty': qty, 'time': formatted_time, 'asset': asset_lbl})

                elif position == 1:
                    # CLOSE LONG (SELL) & REVERSE TO SHORT
                    if is_option:
                        opt_type = signal_type_override or getattr(self.strategy, 'type', 'CE')
                        pnl, _ = simulate_option_pnl(entry_price, current_spot_price, entry_strike, opt_type, entry_qty)
                        invested_capital = entry_price * entry_qty
                        asset_lbl = f"OPT_{entry_strike}_{opt_type}"
                    else:
                        pnl = (trade_price - entry_price) * entry_qty
                        invested_capital = CAPITAL
                        asset_lbl = "TRADE_ASSET"
                        
                    self.results['total_return'] += pnl
                    pnl_percent = (pnl / invested_capital) * 100 if invested_capital > 0 else 0.0
                    cum_pnl_percent = (self.results['total_return'] / CAPITAL) * 100

                    self.results['trades'].append({
                        'type': 'SELL', 'price': trade_price, 'pnl': pnl, 'qty': entry_qty, 
                        'pnl_percent': round(pnl_percent, 2), 'cum_pnl_percent': round(cum_pnl_percent, 2),
                        'time': formatted_time, 'asset': asset_lbl
                    })
                    
                    # New Short
                    position = -1
                    entry_price = trade_price if not is_option else current_spot_price
                    entry_qty = qty
                    if is_option:
                         step = get_strike_step(self.signal_token)
                         entry_strike = get_atm_strike(current_spot_price, step)
                         asset_lbl = f"OPT_{entry_strike}_{getattr(self.strategy, 'type', 'CE')}"
                    self.results['trades'].append({'type': 'SELL', 'price': entry_price, 'qty': qty, 'time': formatted_time, 'asset': asset_lbl})
            
            # Handle EXIT / COVER signals
            elif action == 'EXIT':
                if position != 0:
                     if is_option:
                         opt_type = signal_type_override or getattr(self.strategy, 'type', 'CE')
                         pnl, _ = simulate_option_pnl(entry_price, current_spot_price, entry_strike, opt_type, entry_qty)
                         invested_capital = entry_price * entry_qty
                         if position == -1: pnl = -pnl
                         asset_lbl = f"OPT_{entry_strike}_{opt_type}"
                     else:
                         pnl = (trade_price - entry_price) * entry_qty if position == 1 else (entry_price - trade_price) * entry_qty
                         invested_capital = CAPITAL
                         asset_lbl = "TRADE_ASSET"
                         
                     self.results['total_return'] += pnl
                     pnl_percent = (pnl / invested_capital) * 100 if invested_capital > 0 else 0.0
                     cum_pnl_percent = (self.results['total_return'] / CAPITAL) * 100
  
                     type_lbl = 'SELL' if position == 1 else 'COVER'
                     self.results['trades'].append({
                        'type': type_lbl, 'price': trade_price, 'pnl': pnl, 'qty': entry_qty, 
                        'pnl_percent': round(pnl_percent, 2), 'cum_pnl_percent': round(cum_pnl_percent, 2),
                        'time': formatted_time, 'asset': asset_lbl, 'note': 'Signal_Exit'
                     })
                     position = 0

            elif action == 'COVER':
                if position == -1:
                     if is_option:
                         opt_type = signal_type_override or getattr(self.strategy, 'type', 'CE')
                         pnl, _ = simulate_option_pnl(entry_price, current_spot_price, entry_strike, opt_type, entry_qty)
                         invested_capital = entry_price * entry_qty
                         pnl = -pnl
                         asset_lbl = f"OPT_{entry_strike}_{opt_type}"
                     else:
                         pnl = (entry_price - trade_price) * entry_qty
                         invested_capital = CAPITAL
                         asset_lbl = "TRADE_ASSET"
                         
                     self.results['total_return'] += pnl
                     pnl_percent = (pnl / invested_capital) * 100 if invested_capital > 0 else 0.0
                     cum_pnl_percent = (self.results['total_return'] / CAPITAL) * 100
                     
                     self.results['trades'].append({
                        'type': 'COVER', 'price': trade_price, 'pnl': pnl, 'qty': entry_qty, 
                        'pnl_percent': round(pnl_percent, 2), 'cum_pnl_percent': round(cum_pnl_percent, 2),
                        'time': formatted_time, 'asset': asset_lbl, 'note': 'Signal_Cover'
                     })
                     position = 0

        # Close any open position at end
        if position != 0:
             last_price_sig = data.iloc[-1]['close_sig']
             last_price_trd = data.iloc[-1]['close_trd']
             
             if is_nifty_equity:
                 last_price_trd = last_price_trd / 100.0
             
             last_time_str = data.iloc[-1]['timestamp'].strftime('%d-%m-%Y %H:%M')

             if is_option:
                 opt_type = signal_type_override or getattr(self.strategy, 'type', 'CE')
                 pnl, _ = simulate_option_pnl(entry_price, last_price_sig, entry_strike, opt_type, entry_qty)
                 invested_capital = entry_price * entry_qty
                 if position == -1: pnl = -pnl
                 asset_lbl = f"OPT_{entry_strike}_{opt_type}"
             else:
                 pnl = (last_price_trd - entry_price) * entry_qty if position == 1 else (entry_price - last_price_trd) * entry_qty
                 invested_capital = CAPITAL
                 asset_lbl = "TRADE_ASSET"
                 
             self.results['total_return'] += pnl
             pnl_percent = (pnl / invested_capital) * 100 if invested_capital > 0 else 0.0
             cum_pnl_percent = (self.results['total_return'] / CAPITAL) * 100
                 
             type_lbl = 'SELL' if position == 1 else 'COVER'
             
             self.results['trades'].append({
                'type': type_lbl, 
                'price': last_price_trd, 
                'pnl': pnl, 
                'qty': entry_qty, 
                'pnl_percent': round(pnl_percent, 2),
                'cum_pnl_percent': round(cum_pnl_percent, 2),
                'time': last_time_str,
                'asset': asset_lbl,
                'note': 'SquareOff_Final'
             })

        if not self.silent:
            print("Backtest completed.")
            print(f"Total Return: {self.results['total_return']}")
        return self.results
