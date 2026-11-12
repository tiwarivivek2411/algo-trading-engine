from .smart_api_client import SmartAPIClient
from .risk_manager import RiskManager
from .logger import TradeLogger
from .ticker import Ticker
from .tick_logger import TickLogger
import time
import pandas as pd

class LiveTrader:
    def __init__(self, api_client: SmartAPIClient, strategy, symbol, token, strategy_name="Unknown", interval="FIVE_MINUTE", total_capital=100000, use_websocket=False):
        self.api_client = api_client
        self.strategy = strategy
        self.symbol = symbol # e.g., "SBIN-EQ"
        self.token = token   # e.g., "3045"
        self.interval = interval
        self.total_capital = total_capital
        self.risk_manager = RiskManager()
        self.is_running = False
        self.use_websocket = use_websocket
        self.ticker = None
        self.tick_logger = TickLogger() if use_websocket else None
        self.logger = TradeLogger(strategy_name)

    def start(self):
        """
        Starts the live trading loop.
        """
        self.is_running = True
        print(f"Starting live trading for {self.symbol} ({self.token}) with strategy...")
        
        # Initial Login Verify
        if not self.api_client.session_data:
            # Try browser login if not authenticated
            if not self.api_client.login_via_browser():
                print("Failed to login. Aborting.")
                return

        if self.use_websocket:
            print("Initializing WebSocket Ticker...")
            self.ticker = Ticker(self.api_client, [self.token], self.on_tick)
            if not self.ticker.start():
                print("Failed to start ticker. Falling back to polling.")
                self.use_websocket = False

        while self.is_running:
            try:
                # 1. Fetch latest candle
                end_time = time.strftime("%Y-%m-%d %H:%M")
                start_time = time.strftime("%Y-%m-%d 09:15") 
                
                data = self.api_client.fetch_historical_data(
                    self.token, self.interval, start_time, end_time
                )
                
                if not data.empty:
                    latest_candle = data.iloc[-1]
                    self.logger.log_data(f"Fetched Candle: {latest_candle.to_dict()}")
                    
                    # 2. Update Strategy
                    self.strategy.on_data(latest_candle)
                    
                    # 3. Generate Signal
                    signal = self.strategy.generate_signal()
                    
                    if signal != 'HOLD':
                        self.logger.log_signal(f"Generated Signal: {signal} at {latest_candle['close']}")
                    
                    # 4. Execute
                    current_price = latest_candle['close']
                    quantity = self.risk_manager.calculate_quantity(current_price, self.total_capital)
                    
                    if quantity > 0:
                        if signal == 'BUY':
                            log_msg = f"Executing BUY. Price: {current_price}, Qty: {quantity}"
                            print(log_msg)
                            self.logger.log_order(log_msg)
                            
                            sl_price = self.risk_manager.calculate_stoploss(current_price, "EQUITY_INTRADAY")
                            
                            order_id = self.api_client.place_order(
                                symbol=self.symbol,
                                token=self.token,
                                transaction_type="BUY",
                                quantity=quantity,
                                stoploss=sl_price
                            )
                            if order_id:
                                self.logger.log_order(f"Order Placed ID: {order_id}")

                        elif signal == 'SELL':
                             log_msg = f"Executing SELL. Price: {current_price}, Qty: {quantity}"
                             print(log_msg)
                             self.logger.log_order(log_msg)
                             
                             order_id = self.api_client.place_order(
                                symbol=self.symbol,
                                token=self.token,
                                transaction_type="SELL",
                                quantity=quantity
                            )
                             if order_id:
                                self.logger.log_order(f"Order Placed ID: {order_id}")
                    else:
                        print("Calculated quantity is 0. Insufficient capital.")
                
                print("Waiting for next cycle...")
                time.sleep(60) # Poll every minute
                
            except KeyboardInterrupt:
                print("Stopping live trader...")
                self.is_running = False
            except Exception as e:
                print(f"Error in trading loop: {e}")
                time.sleep(10)
        
        if self.ticker:
            self.ticker.stop()
        if self.tick_logger:
            self.tick_logger.close()

    def on_tick(self, tick_data):
        """
        Callback for handling tick data from WebSocket.
        """
        try:
            ltp = tick_data.get('last_traded_price', 0) / 100.0 # Price is in paise
            token = tick_data.get('token')
            
            if ltp > 0:
                self.logger.log_data(f"Tick received: {token} @ {ltp}")
                
                # Log tick to file for future backtesting
                if self.tick_logger:
                    self.tick_logger.log_tick(tick_data)
                
                # Create a pseudo-candle for the strategy until a real one arrives
                # Most strategies can work with just 'close' if they are trend following
                tick_candle = pd.Series({
                    'timestamp': pd.Timestamp.now(),
                    'open': ltp,
                    'high': ltp,
                    'low': ltp,
                    'close': ltp,
                    'volume': 0
                })
                
                # Update Strategy and check for signals
                self.strategy.on_data(tick_candle)
                self.check_and_execute_signals(ltp)
                
        except Exception as e:
            print(f"Error in LiveTrader.on_tick: {e}")

    def check_and_execute_signals(self, current_price):
        """
        Generates signal from strategy and executes order if necessary.
        """
        signal = self.strategy.generate_signal()
        
        if signal != 'HOLD':
            self.logger.log_signal(f"Signal generated: {signal} at {current_price}")
            quantity = self.risk_manager.calculate_quantity(current_price, self.total_capital)
            
            if quantity > 0:
                if signal == 'BUY':
                    sl_price = self.risk_manager.calculate_stoploss(current_price, "EQUITY_INTRADAY")
                    self.api_client.place_order(
                        symbol=self.symbol,
                        token=self.token,
                        transaction_type="BUY",
                        quantity=quantity,
                        stoploss=sl_price
                    )
                elif signal == 'SELL':
                    self.api_client.place_order(
                        symbol=self.symbol,
                        token=self.token,
                        transaction_type="SELL",
                        quantity=quantity
                    )
