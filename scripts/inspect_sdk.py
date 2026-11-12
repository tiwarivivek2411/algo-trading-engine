from SmartApi import SmartConnect
import inspect

print("Methods in SmartConnect:")
methods = [method_name for method_name in dir(SmartConnect) if callable(getattr(SmartConnect, method_name))]
for m in methods:
    print(m)
