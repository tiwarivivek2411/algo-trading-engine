import json
import sys
from src.smart_api_client import SmartAPIClient
import pandas as pd
from datetime import datetime, timedelta

def load_config(path="config.json"):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}

def verify():
    config = load_config()
    credentials = config.get("credentials", {})
    
    api_key = credentials.get("api_key")
    client_code = credentials.get("client_code")
    secret_key = credentials.get("secret_key")
    
    print(f"Attempting login via browser...")

    client = SmartAPIClient(api_key, client_code, secret_key)
    
    # This should trigger log_error if it fails
    if not client.login_via_browser():
        print("Login Failed")
        return

    print("Login Successful. Fetching Historical Data...")
    # Fetch attempts
    to_date = datetime.now()
    from_date = to_date - timedelta(days=5)
    
    data = client.fetch_historical_data(
        token="3045", 
        interval="ONE_DAY",
        from_date=from_date.strftime("%Y-%m-%d %H:%M"),
        to_date=to_date.strftime("%Y-%m-%d %H:%M")
    )
    
    if not data.empty:
        print("Historical Data Fetched!")
    else:
        print("Failed to fetch data")

if __name__ == "__main__":
    verify()
