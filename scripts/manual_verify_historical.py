import json
import sys
import os

# Add parent directory to path so we can import src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.smart_api_client import SmartAPIClient
from datetime import datetime, timedelta
import pandas as pd

def verify():
    # Load config
    with open("config.json", 'r') as f:
        config = json.load(f)
    creds = config.get("credentials", {})
    
    api_key = creds.get("api_key")
    client_code = creds.get("client_code")
    secret_key = creds.get("secret_key")
    
    client = SmartAPIClient(api_key, client_code, secret_key)
    
    # Manual Token Injection (from Chat Step 666)
    auth_token = "eyJhbGciOiJIUzUxMiJ9.eyJ1c2VybmFtZSI6IkREVlUwNzAiLCJyb2xlcyI6MCwidXNlcnR5cGUiOiJVU0VSIiwidG9rZW4iOiJleUpoYkdjaU9pSlNVekkxTmlJc0luUjVjQ0k2SWtwWFZDSjkuZXlKMWMyVnlYM1I1Y0dVaU9pSmpiR2xsYm5RaUxDSjBiMnRsYmw5MGVYQmxJam9pZEhKaFpHVmZZV05qWlhOelgzUnZhMlZ1SWl3aVoyMWZhV1FpT2pFd01pd2ljMjkxY21ObElqb2lNeUlzSW1SbGRtbGpaVjlwWkNJNklqVmlOak16TWpJekxXSmlOamN0TXpsbE15MWlaV1V3TFRnd1pUWTNOMkZpTldWbU1TSXNJbXRwWkNJNkluUnlZV1JsWDJ0bGVWOTJNaUlzSW05dGJtVnRZVzVoWjJWeWFXUWlPakV3TWl3aWNISnZaSFZqZEhNaU9uc2laR1Z0WVhRaU9uc2ljM1JoZEhWeklqb2lZV04wYVhabEluMHNJbTFtSWpwN0luTjBZWFIxY3lJNkltRmpkR2wyWlNKOWZTd2lhWE56SWpvaWRISmhaR1ZmYkc5bmFXNWZjMlZ5ZG1salpTSXNJbk4xWWlJNklrUkVWbFV3TnpBaUxDSmxlSEFpT2pFM05qYzFPRFV6TURZc0ltNWlaaUk2TVRjMk56UTVPRGN5Tml3aWFXRjBJam94TnpZM05EazROekkyTENKcWRHa2lPaUk1TlRoaU9UTTJPUzB6TUdJM0xUUmhaVEl0T0RZeE5pMDBPR0ZrWVRRME9ERTNNakVpTENKVWIydGxiaUk2SWlKOS5EQ05UblFlc3BYSE85a1hRejU2QXRlcUN0R3lmR21Rc29mUEFNMy1TVWNGMFhKLU5SVFN5TlZEVDBldEZXR1NyY2hxeVl0OG1LSnUxTzVFRUd0eF8wN0U3LXcyQ2FhWGZwcU43QkhhSXZaT2VicUJTN19DUTBOT1lmdnpVOEI1dGZRUGhSVENuejRtQWNEY1lZZFNBUjRFWGFNNXlaak9oNUo0R3ZlR2VlS00iLCJBUEktS0VZIjoiaE1aRmRpdHEiLCJYLU9MRC1BUEktS0VZIjpmYWxzZSwiaWF0IjoxNzY3NDk4OTA2LCJleHAiOjE3Njc1NTE0MDB9.-cchO5hEJY-dJXLHGEVl29dOLImYWCylwNidnmbT6KJwFR7m4jrRgVAZAhBfeSzQdas_ABSlYnSVe9LD0w_GWQ"
    feed_token = "eyJhbGciOiJIUzUxMiJ9.eyJ1c2VybmFtZSI6IkREVlUwNzAiLCJpYXQiOjE3Njc0OTg5MDYsImV4cCI6MTc2NzU4NTMwNn0.p4tehTJeYi8lUeAPbJLWPvNiagTkfLgc9LX27pRswst-EMsn7xq0MvSto76UOAWFW8VIIgcefhZj_wKbwJnbaw"
    refresh_token = "eyJhbGciOiJIUzUxMiJ9.eyJ0b2tlbiI6IlJFRlJFU0gtVE9LRU4iLCJSRUZSRVNILVRPS0VOIjoiZXlKaGJHY2lPaUpTVXpJMU5pSXNJblI1Y0NJNklrcFhWQ0o5LmV5SjFjMlZ5WDNSNWNHVWlPaUpqYkdsbGJuUWlMQ0owYjJ0bGJsOTBlWEJsSWpvaWRISmhaR1ZmY21WbWNtVnphRjkwYjJ0bGJpSXNJbWR0WDJsa0lqb3dMQ0p6YjNWeVkyVWlPaUl6SWl3aVpHVjJhV05sWDJsa0lqb2lOV0kyTXpNeU1qTXRZbUkyTnkwek9XVXpMV0psWlRBdE9EQmxOamMzWVdJMVpXWXhJaXdpYTJsa0lqb2lkSEpoWkdWZmEyVjVYM1l5SWl3aWIyMXVaVzFoYm1GblpYSnBaQ0k2TUN3aWFYTnpJam9pYkc5bmFXNWZjMlZ5ZG1salpTSXNJbk4xWWlJNklrUkVWbFV3TnpBaUxDSmxlSEFpT2pFM05qYzFPRFV6TURZc0ltNWlaaUk2TVRjMk56UTVPRGN5Tml3aWFXRjBJam94TnpZM05EazROekkyTENKcWRHa2lPaUkzT1dVNE16RmpPUzA0TXpRNExUUm1ZelV0T0RGbU9DMDROemczTkdJMU1EUXdNVGdpTENKVWIydGxiaUk2SWlKOS5QNkYxYWk1ZnpFaWFvRWRWclRGckxpR19JN0pqQ0F3TUJWUXRPbVZkbVNrR3lwMkdySmlYb3N3RmZzNV9CdjlyTXVzNWhVSC02b2JlelBiOFFkWllwUXczUmFSdnlmREpPTjk4OTQzZHhGaEQ0dThva0F3a1Y3T3dMQVpKRmxGUnBBRGxRVUxjbExUd1FfTENpa2hPeFlJaGQzUGJod0FtWnJUVUM4bld3Z2MiLCJpYXQiOjE3Njc0OTg5MDZ9.Eg-NOlkU0OZMsnukSbenLiteWJKjyB1GqH8qIZVzOEetfF0qkozwPudXf2Wuyq1fSkmnjrhim_9D-li4PKmT2Q"
    
    client.smart_api.setAccessToken(auth_token)
    client.smart_api.setFeedToken(feed_token)
    client.smart_api.setRefreshToken(refresh_token)
    client.smart_api.setUserId(client_code)
    
    print("Tokens set manually. Fetching Historical Data...")
    
    # Test for last 30 days
    to_date = datetime.now()
    from_date = to_date - timedelta(days=30)
    
    data = client.fetch_historical_data(
        token="3045",  # SBIN
        interval="ONE_DAY",
        from_date=from_date.strftime("%Y-%m-%d %H:%M"),
        to_date=to_date.strftime("%Y-%m-%d %H:%M")
    )
    
    if not data.empty:
        print("Historical Data Fetched Successfully:")
        print(data)
    else:
        print("Failed to fetch data")

if __name__ == "__main__":
    verify()
