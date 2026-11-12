# 📈 Algo Trading Engine

A modular Python algorithmic trading framework supporting live market execution, strategy backtesting, screening, and WebSocket streaming via SmartAPI.

## 🚀 Features
- **Strategy Suite**:
  - `momentum`: Intraday & swing momentum breakouts
  - `supertrend`: Multi-timeframe trend following
  - `goldencross`: 50/200 EMA & SMA crossover trend filter
  - `bollinger`: Bollinger Bands volatility squeeze breakout
  - `fno_directional`: F&O index directional execution
- **Execution Modules**:
  - Live order execution and position sizing
  - WebSocket market data feed listener
  - Historical backtesting engine with performance metrics
  - Automated screening across Nifty 50 and Midcap universes

## 🛠️ Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/tiwarivivek2411/algo-trading-engine.git
   cd algo-trading-engine
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in your API credentials:
   ```bash
   cp .env.example .env
   ```
4. Run backtests or live trading:
   ```bash
   python main.py --mode backtest --strategy momentum
   ```
