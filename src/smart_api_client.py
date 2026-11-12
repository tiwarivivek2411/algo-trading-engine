import requests
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from SmartApi import SmartConnect
from SmartApi.smartWebSocketV2 import SmartWebSocketV2
import pandas as pd
from datetime import datetime
from .logger import log_error
import os
import json
import socket

def get_public_ip():
    try:
        return requests.get('https://api.ipify.org').text
    except:
        return "127.0.0.1"

class SmartAPIClient:
    def __init__(self, api_key, client_code, secret_key):
        self.api_key = api_key
        self.client_code = client_code
        self.secret_key = secret_key
        self.public_ip = get_public_ip()
        self.smart_api = SmartConnect(api_key=self.api_key)
        self.session_data = None
        self.auth_token = None
        self.refresh_token = None
        self.feed_token = None

    def login_via_browser(self):
        """
        Initiates browser-based login flow (Publisher Login).
        Starts a local server to capture the auth token from the redirect.
        """
        # 1. Try to load existing tokens first
        if self._load_tokens():
            print("Successfully logged in using saved tokens.")
            return True

        try:
            # Create a simple handler to capture the token
            captured_data = {}
            
            class AuthHandler(BaseHTTPRequestHandler):
                def do_POST(self):
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length).decode('utf-8')
                    captured_data['post_body'] = post_data
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(b"<h1>Login Successful!</h1><p>You can close this tab.</p>")
                    threading.Thread(target=httpd.shutdown).start()

                def do_GET(self):
                    query = urlparse(self.path).query
                    captured_data['query'] = query
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(b"<h1>Login Successful!</h1><p>Tokens captured. You can close this tab.</p>")
                    threading.Thread(target=httpd.shutdown).start()

            # Start server (not strictly used for the manual paste flow but good to have)
            server_address = ('127.0.0.1', 8080)
            httpd = HTTPServer(server_address, AuthHandler)
            
            login_url = f"https://smartapi.angelone.in/publisher-login?api_key={self.api_key}"
            print(f"\n--- ATTENTION REQUIRED ---")
            print(f"1. Please log in via your browser at:")
            print(f"   {login_url}")
            print(f"2. After Login, if you are redirected to a 404 page or 'localhost', COPY the ENTIRE URL from the address bar.")
            print(f"3. PASTE the URL below:")
            print(f"--------------------------")
            
            # Open browser automatically
            webbrowser.open(login_url)
            
            # Allow manual paste of the URL (since redirect config might be broken)
            redirected_url = input("Paste the Resulting URL here: ").strip()
            
            # Parse the pasted URL
            parsed = urlparse(redirected_url)
            params = parse_qs(parsed.query)
            
            # Also check fragments just in case
            if not params:
                params = parse_qs(parsed.fragment)

            auth_token = params.get('auth_token', [None])[0]
            feed_token = params.get('feed_token', [None])[0]
            refresh_token = params.get('refresh_token', [None])[0]
            
            if auth_token:
                    self.auth_token = auth_token
                    self.feed_token = feed_token
                    self.refresh_token = refresh_token
                    
                    self.smart_api.setAccessToken(self.auth_token)
                    self.smart_api.setFeedToken(self.feed_token)
                    self.smart_api.setRefreshToken(self.refresh_token)
                    self.smart_api.setUserId(self.client_code)
                    
                    self.session_data = {
                        "jwtToken": self.auth_token,
                        "refreshToken": self.refresh_token,
                        "feedToken": self.feed_token
                    }
                    self._save_tokens() # Save tokens after successful login
                    
                    print("Successfully logged in via Manual URL Paste!")
                    return True
            
            print("Failed to extract auth_token from pasted URL.")
            return False

        except Exception as e:
            msg = f"Error during browser login: {e}"
            print(msg)
            log_error(e, "SmartAPIClient.login_via_browser")
            return False

    def _save_tokens(self):
        """Saves current session tokens to tokens.json"""
        try:
             with open("tokens.json", "w") as f:
                 json.dump(self.session_data, f)
             print("Tokens saved to tokens.json")
        except Exception as e:
            print(f"Failed to save tokens: {e}")

    def _load_tokens(self):
        """Attempts to load and validate tokens from tokens.json"""
        if not os.path.exists("tokens.json"):
            return False
            
        try:
            with open("tokens.json", "r") as f:
                data = json.load(f)
                
            self.session_data = data
            self.auth_token = data.get("jwtToken")
            self.feed_token = data.get("feedToken")
            self.refresh_token = data.get("refreshToken")
            
            if not self.auth_token:
                return False

            self.smart_api.setAccessToken(self.auth_token)
            self.smart_api.setFeedToken(self.feed_token)
            self.smart_api.setRefreshToken(self.refresh_token)
            self.smart_api.setUserId(self.client_code)
            
            return True
        except Exception as e:
            print(f"Failed to load tokens: {e}")
            return False

    def fetch_historical_data(self, token, interval, from_date, to_date, exchange="NSE"):
        """
        Fetches historical candle data with automatic chunking for long durations.
        Includes file-based caching for faster subsequent runs.
        """
        try:
            # 1. Check Cache first
            cache_dir = os.path.join("data", "historical")
            os.makedirs(cache_dir, exist_ok=True)
            
            # Clean dates for filename
            f_clean = from_date.replace(" ", "_").replace(":", "")
            t_clean = to_date.replace(" ", "_").replace(":", "")
            cache_file = os.path.join(cache_dir, f"{token}_{interval}_{f_clean}_{t_clean}.csv")
            
            if os.path.exists(cache_file):
                print(f"Loading data from cache: {cache_file}")
                df = pd.read_csv(cache_file)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                return df

            print(f"Fetching {interval} data for Token {token} from API ({from_date} to {to_date})...")

            # Parse dates
            start_dt = datetime.strptime(from_date, "%Y-%m-%d %H:%M")
            end_dt = datetime.strptime(to_date, "%Y-%m-%d %H:%M")
            
            # Define max days per request based on interval
            if "MINUTE" in interval:
                max_days = 20 # Safe limit
            else:
                max_days = 90
            
            all_dfs = []
            current_start = start_dt
            
            while current_start < end_dt:
                current_end = current_start + pd.Timedelta(days=max_days)
                if current_end > end_dt:
                    current_end = end_dt
                
                # Format for API
                f_date = current_start.strftime("%Y-%m-%d %H:%M")
                t_date = current_end.strftime("%Y-%m-%d %H:%M")
                
                historic_param = {
                    "exchange": exchange,
                    "symboltoken": token,
                    "interval": interval,
                    "fromdate": f_date,
                    "todate": t_date
                }
                
                data = self.smart_api.getCandleData(historic_param)
                
                if data and data.get('status') and data.get('data'):
                     columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                     chunk_df = pd.DataFrame(data['data'], columns=columns)
                     # Convert timestamp and numeric columns
                     chunk_df['timestamp'] = pd.to_datetime(chunk_df['timestamp'])
                     chunk_df[['open', 'high', 'low', 'close', 'volume']] = chunk_df[['open', 'high', 'low', 'close', 'volume']].apply(pd.to_numeric)
                     all_dfs.append(chunk_df)
                
                # Calculate next start time based on interval
                minute_map = {
                    "ONE_MINUTE": 1, "THREE_MINUTE": 3, "FIVE_MINUTE": 5, 
                    "FIFTEEN_MINUTE": 15, "THIRTY_MINUTE": 30, "ONE_HOUR": 60,
                    "ONE_DAY": 1440
                }
                delta_mins = minute_map.get(interval, 1440) # Default to 1 day
                current_start = current_end + pd.Timedelta(minutes=delta_mins)
                
                # Rate Limit Prevention
                import time
                time.sleep(0.4)

            if not all_dfs:
                return pd.DataFrame()

            final_df = pd.concat(all_dfs).drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
            
            # Save to Cache
            final_df.to_csv(cache_file, index=False)
            print(f"Data cached to: {cache_file}")

            return final_df

        except Exception as e:
            print(f"Error fetching historical data: {e}")
            log_error(e, f"SmartAPIClient.fetch_historical_data (Token: {token})")
            return pd.DataFrame()

    def place_order(self, symbol, token, transaction_type, quantity, order_type="MARKET", product_type="INTRADAY", price=0.0, stoploss=0.0):
        """
        Places an order.
        """
        try:
            order_params = {
                "variety": "NORMAL",
                "tradingsymbol": symbol,
                "symboltoken": token,
                "transactiontype": transaction_type,
                "exchange": "NSE",
                "ordertype": order_type,
                "producttype": product_type,
                "duration": "DAY",
                "price": price,
                "squareoff": "0",
                "stoploss": str(stoploss),
                "quantity": quantity
            }
            
            order_id = self.smart_api.placeOrder(order_params)
            print(f"Order placed. ID: {order_id}")
            return order_id
            
        except Exception as e:
            print(f"Error placing order: {e}")
            log_error(e, f"SmartAPIClient.place_order (Symbol: {symbol})")
            return None

    def get_ticker(self):
        """
        Returns a SmartWebSocketV2 instance using the current session tokens.
        """
        if not self.auth_token or not self.feed_token:
            if not self._load_tokens():
                print("No session tokens available. Please login first.")
                return None
        
        return SmartWebSocketV2(
            auth_token=self.auth_token,
            api_key=self.api_key,
            client_code=self.client_code,
            feed_token=self.feed_token
        )
