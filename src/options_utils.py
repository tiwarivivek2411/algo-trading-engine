import math

# Lot Sizes for Top FNO Stocks (Approximate for 2024-25)
LOT_SIZES = {
    "NIFTY": 50,
    "BANKNIFTY": 15,
    "FINNIFTY": 40,
    "SBIN": 1500,
    "RELIANCE": 250,
    "HDFCBANK": 550,
    "INFY": 400,
    "ICICIBANK": 700,
    "TCS": 175,
    "ITC": 1600,
    "KOTAKBANK": 400,
    "LT": 300,
    "AXISBANK": 625,
    "HINDUNILVR": 300,
    "BHARTIARTL": 950,
    "BAJFINANCE": 125,
    "ASIANPAINT": 200,
    "MARUTI": 50,
    "TITAN": 175,
    "ULTRACEMCO": 100,
    "SUNPHARMA": 700,
    "M&M": 350
}

STRIKE_STEPS = {
    "NIFTY": 50,
    "BANKNIFTY": 100,
    "FINNIFTY": 50,
    "SBIN": 5,
    "RELIANCE": 20,
    "HDFCBANK": 10,
    "INFY": 10,
    "ICICIBANK": 10,
    "TCS": 20,
    # Default fallback
    "DEFAULT": 10 
}

def get_lot_size(symbol):
    """Returns lot size for a symbol, defaulting to 1 for equity."""
    # Handle Nifty 50 vs NIFTY match
    if "NIFTY" in symbol and "BANK" not in symbol and "FIN" not in symbol:
        return LOT_SIZES.get("NIFTY")
    return LOT_SIZES.get(symbol, 1) # Default to 1 (Equity) if not found in list

def get_strike_step(symbol):
    sym = str(symbol)
    if "NIFTY" in sym and "BANK" not in sym and "FIN" not in sym:
        return STRIKE_STEPS.get("NIFTY")
    if sym == "99926000": # Nifty 50 Spot
        return STRIKE_STEPS.get("NIFTY")
    if sym == "99926009": # BankNifty Spot
        return STRIKE_STEPS.get("BANKNIFTY")
    return STRIKE_STEPS.get(symbol, STRIKE_STEPS["DEFAULT"])

def get_atm_strike(spot_price, step):
    """Calculates ATM strike based on spot price and step size."""
    return round(spot_price / step) * step

def calculate_option_delta(spot, strike, time_to_expiry_days, option_type="CE"):
    """
    Approximates Option Delta for backtesting simulation.
    Uses simple rule-of-thumb logic since we don't have live Greeks.
    
    ATM: ~0.5
    ITM (Deep): -> 1.0
    OTM (Deep): -> 0.0
    """
    moneyness = spot / strike
    
    if option_type == "CE":
        if 0.99 <= moneyness <= 1.01: return 0.5  # ATM
        if moneyness > 1.05: return 0.8           # Deep ITM
        if moneyness > 1.02: return 0.6           # ITM
        if moneyness < 0.95: return 0.2           # Deep OTM
        if moneyness < 0.98: return 0.3           # OTM
        return 0.4 # Near OTM
    
    elif option_type == "PE":
        # Deltas are negative for Puts, but we return magnitude for PnL calc usually
        # Adjusted to match moneyness logic for Puts
        if 0.99 <= moneyness <= 1.01: return -0.5 # ATM
        if moneyness < 0.95: return -0.8          # Deep ITM
        if moneyness < 0.98: return -0.6          # ITM
        if moneyness > 1.05: return -0.2          # Deep OTM
        if moneyness > 1.02: return -0.3          # OTM
        return -0.4 # Near OTM
        
    return 0.0

def simulate_option_pnl(entry_spot, exit_spot, strike, option_type, quantity, delta=None):
    """
    Simulates PnL for an option trade based on Spot movement and Delta.
    PnL = (Spot_Change * Delta) * Quantity
    """
    spot_change = exit_spot - entry_spot
    
    if delta is None:
        # Auto-calc delta based on Entry (approximation)
        delta = calculate_option_delta(entry_spot, strike, 30, option_type)
        
    # Example: Spot goes 100 -> 110 (+10). CE Delta 0.5. Prem Change = +5.
    # Example: Spot goes 100 -> 90 (-10). PE Delta -0.5. Prem Change = (-10 * -0.5) = +5.
    
    premium_change = spot_change * delta
    pnl = premium_change * quantity
    return pnl, round(premium_change, 2)
