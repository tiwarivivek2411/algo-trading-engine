import threading
import time
from .smart_api_client import SmartAPIClient
from .logger import log_error

class Ticker:
    def __init__(self, api_client: SmartAPIClient, tokens, callback):
        """
        Initializes the Ticker for real-time data.
        
        :param api_client: Instance of SmartAPIClient
        :param tokens: List of tokens to subscribe to (e.g., ["99926000"])
        :param callback: Function to call when new data arrives
        """
        self.api_client = api_client
        self.tokens = tokens
        self.callback = callback
        self.ws = None
        self.thread = None
        self.is_running = False

    def on_data(self, wsapp, data):
        """Callback for receiving tick data."""
        try:
            # SmartWebSocketV2 parses the binary data for us
            # data contains: last_traded_price, sequence_number, exchange_timestamp, etc.
            if self.callback:
                self.callback(data)
        except Exception as e:
            print(f"Error in Ticker.on_data: {e}")
            log_error(e, "Ticker.on_data")

    def on_open(self, wsapp):
        """Callback when connection is established."""
        print("WebSocket Connection Opened. Subscribing to tokens...")
        # NSE_CM is 1, Mode 1 is LTP
        token_list = [{"exchangeType": 1, "tokens": self.tokens}]
        self.ws.subscribe("correlation_id_123", 1, token_list)

    def on_error(self, wsapp, error):
        """Callback when an error occurs."""
        print(f"WebSocket Error: {error}")
        log_error(Exception(error), "Ticker.on_error")

    def on_close(self, wsapp):
        """Callback when connection is closed."""
        print("WebSocket Connection Closed")

    def start(self):
        """Starts the WebSocket in a separate thread."""
        self.ws = self.api_client.get_ticker()
        if not self.ws:
            return False

        self.ws.on_data = self.on_data
        self.ws.on_open = self.on_open
        self.ws.on_error = self.on_error
        self.ws.on_close = self.on_close

        self.is_running = True
        self.thread = threading.Thread(target=self.ws.connect)
        self.thread.daemon = True
        self.thread.start()
        print("Ticker started in background thread.")
        return True

    def stop(self):
        """Stops the WebSocket connection."""
        self.is_running = False
        if self.ws:
            self.ws.close_connection()
        if self.thread:
            self.thread.join(timeout=2)
        print("Ticker stopped.")

if __name__ == "__main__":
    # Test block
    from .smart_api_client import SmartAPIClient
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    client = SmartAPIClient(
        api_key=os.getenv("ANGEL_API_KEY"),
        client_code=os.getenv("ANGEL_CLIENT_ID"),
        secret_key=os.getenv("ANGEL_SECRET_KEY")
    )
    
    def test_callback(data):
        print(f"Tick received: {data}")

    ticker = Ticker(client, ["99926000"], test_callback) # Nifty
    if ticker.start():
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            ticker.stop()
