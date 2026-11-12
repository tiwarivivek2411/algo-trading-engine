from SmartApi import SmartConnect
import inspect

# Print the source of requestHeaders method if it exists, or look for where headers are defined.
if hasattr(SmartConnect, 'requestHeaders'):
    print("Source of requestHeaders:")
    print(inspect.getsource(SmartConnect.requestHeaders))
else:
    print("requestHeaders method not found. checking _postRequest")
    print(inspect.getsource(SmartConnect._postRequest))
