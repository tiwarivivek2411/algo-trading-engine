import requests
import json

def load_config(path="config.json"):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}

def test_publisher_url():
    config = load_config()
    credentials = config.get("credentials", {})
    
    # User's current config has UUID in 'mpin' and short string in 'api_key'
    # The URL requires api_key. We'll try both just to be sure.
    
    api_key_from_config = credentials.get("api_key") 
    mpin_from_config = credentials.get("mpin") # This looks like the REAL api key
    
    print(f"Current Config API Key: {api_key_from_config}")
    print(f"Current Config MPIN (looks like API Key): {mpin_from_config}")

    # Try 1: Using the configured api_key
    url1 = f"https://smartapi.angelone.in/publisher-login?api_key={api_key_from_config}&state=test"
    print(f"\n--- Attempt 1: {url1} ---")
    try:
        res1 = requests.get(url1)
        print(f"Status: {res1.status_code}")
        print(f"Content Start: {res1.text[:200]}") # Likely HTML
    except Exception as e:
        print(f"Error: {e}")

    # Try 2: Using the 'mpin' value as api_key (since it looks like a UUID)
    url2 = f"https://smartapi.angelone.in/publisher-login?api_key={mpin_from_config}&state=test"
    print(f"\n--- Attempt 2: {url2} ---")
    try:
        res2 = requests.get(url2)
        print(f"Status: {res2.status_code}")
        print(f"Content Start: {res2.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_publisher_url()
