import json
import math

class RiskManager:
    def __init__(self, config_path="config.json"):
        self.config = self._load_config(config_path)

    def _load_config(self, path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            return {}

    def calculate_quantity(self, price, total_capital, lot_size=1):
        """
        Calculates the quantity to buy based on:
        1. Max allocation per trade (20,000 INR)
        2. Total Capital check (2 Lakh Max assumed globally if not passed)
        3. Lot Size multiples
        """
        MAX_PER_TRADE = 20000.0
        
        # Determine strict allocation
        allocated_amount = min(MAX_PER_TRADE, total_capital)
        
        if price <= 0:
            return 0
            
        # Raw quantity
        raw_qty = math.floor(allocated_amount / price)
        
        # Adjust for Lot Size
        if lot_size > 1:
            num_lots = math.floor(raw_qty / lot_size)
            final_qty = max(1, num_lots) * lot_size # Buy at least 1 lot if affordable?
            
            # Re-check affordability for 1 lot
            if final_qty * price > MAX_PER_TRADE:
                return 0 # Cannot afford even 1 lot
        else:
            final_qty = max(1, raw_qty) # Asset is equity, buy at least 1
            if final_qty * price > MAX_PER_TRADE:
                return 0 # Cannot afford 1 share
                
        return final_qty

    def calculate_stoploss(self, price, instrument_type="EQUITY_INTRADAY"):
        """
        Calculates stoploss price based on instrument type.
        """
        sl_pct = self.config.get("risk_management", {}).get("stoploss", {}).get(instrument_type, 0.02)
        
        # STOPLOSS is always below price for BUY, logic needs to handle direction
        # But this method is generic 'how much drop allowed'.
        # For simplicity returning the ABSOLUTE SL PRICE for a LONG position
        sl_price = price * (1 - sl_pct)
        return round(sl_price, 2)
