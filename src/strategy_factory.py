from src.universal_strategy import UniversalStrategy
from src.algorithms.keltner_algo import KeltnerAlgorithm
from src.algorithms.stochastic_algo import StochasticAlgorithm
from src.algorithms.rsi_algo import RSIAlgorithm
# ... existing specialized strategies for backward compatibility
from src.strategies.momentum import MomentumStrategy
from src.strategies.supertrend import SupertrendStrategy
from src.strategies.bollinger_squeeze import BollingerSqueezeStrategy

class StrategyFactory:
    @staticmethod
    def generate_strategies():
        strategies = {}
        
        # 1. Define Base Algorithms
        base_algos = {
            "Keltner_Fast": KeltnerAlgorithm(ema_period=10, atr_period=10, multiplier=2.0),
            "Keltner_Std": KeltnerAlgorithm(ema_period=20, atr_period=10, multiplier=2.0),
            "Stoch_5_3": StochasticAlgorithm(k_period=5, d_period=3),
            "Stoch_14_3": StochasticAlgorithm(k_period=14, d_period=3),
            "RSI_Std": RSIAlgorithm(period=14, overbought=70, oversold=30),
            "RSI_Fast": RSIAlgorithm(period=7, overbought=80, oversold=20),
        }

        # 2. Define Execution Modes
        execution_modes = {
            "Eq_Intraday": "EQUITY_INTRADAY",
            "Eq_Positional": "EQUITY_POSITIONAL",
            "Opt_Buy_ATM": {"mode": "OPTION_BUY", "strike": "ATM"},
            "Opt_Buy_ITM1": {"mode": "OPTION_BUY", "strike": "ITM1"},
            "Opt_Buy_OTM1": {"mode": "OPTION_BUY", "strike": "OTM1"},
            "Opt_Sell_ATM": {"mode": "OPTION_SELL", "strike": "ATM"},
            "Opt_Sell_ITM1": {"mode": "OPTION_SELL", "strike": "ITM1"},
            "Opt_Sell_OTM1": {"mode": "OPTION_SELL", "strike": "OTM1"},
        }

        # 3. Generate Universal Combinations
        for algo_name, algo_obj in base_algos.items():
            for mode_name, mode_cfg in execution_modes.items():
                name = f"U_{algo_name}_{mode_name}"
                if isinstance(mode_cfg, dict):
                    strategies[name] = UniversalStrategy(algo_obj, mode_cfg['mode'], strike_offset=mode_cfg['strike'])
                else:
                    strategies[name] = UniversalStrategy(algo_obj, mode_cfg)

        # 4. Keep existing legacy strategies for continuity
        # (Simplified list for now to avoid bloat, can add back as needed)
        strategies["Legacy_Supertrend_10_2"] = SupertrendStrategy(period=10, multiplier=2.0)
        strategies["Legacy_Bollinger_Squeeze"] = BollingerSqueezeStrategy()

        return strategies
