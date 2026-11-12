from SmartApi import SmartConnect
client = SmartConnect(api_key="test")
# Accessing private attribute _routes
print("Available Routes:")
for key, value in client._routes.items():
    print(f"Key: {key}, Path: {value}")
