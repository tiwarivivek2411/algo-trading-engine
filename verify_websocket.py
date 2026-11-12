import os
import time
import json
from src.smart_api_client import SmartAPIClient
from src.ticker import Ticker
from src.tick_logger import TickLogger

def load_config(path="config.json"):
    with open(path, 'r') as f:
        return json.load(f)

def verify_nifty_ticks():
    config = load_config()
    credentials = config.get("credentials", {})
    
    api_key = credentials.get("api_key")
    client_code = credentials.get("client_code")
    secret_key = credentials.get("secret_key")
    
    client = SmartAPIClient(api_key, client_code, secret_key)
    
    # This will require manual login if tokens are expired
    print("Verifying login...")
    if not client.login_via_browser():
        print("Login failed.")
        return

    def on_tick(data):
        print(f"VERIFICATION SUCCESS: Tick received for Nifty: {data}")
        # Log to file
        on_tick.logger.log_tick(data)
        
        # Stop after first few ticks
        on_tick.count += 1
        if on_tick.count >= 5:
            print("Received 5 ticks. Verification complete.")
            on_tick.logger.close()
            os._exit(0)

    on_tick.count = 0
    on_tick.logger = TickLogger(base_dir="data/verification_ticks")
    
    # Nifty Token: 99926000
    ticker = Ticker(client, ["99926000"], on_tick)
    print("Connecting to WebSocket for Nifty (99926000)...")
    if ticker.start():
        try:
            # Wait for ticks
            for _ in range(30):
                time.sleep(1)
            print("Timeout waiting for ticks. Is the market open?")
        except KeyboardInterrupt:
            pass
        finally:
            ticker.stop()

if __name__ == "__main__":
    verify_nifty_ticks()
