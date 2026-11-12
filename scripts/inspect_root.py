from SmartApi import SmartConnect
client = SmartConnect(api_key="test")
print(f"Root URL: {client._rootUrl}")
print(f"Login URL: {client._loginUrl}")
