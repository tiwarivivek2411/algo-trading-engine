# Copilot Instructions for trading

- Root entrypoint: `main.py` controls backtest vs live mode. `--mode backtest` runs `Backtester`, `--mode live` runs `LiveTrader`.
- Primary architecture:
  - `src/smart_api_client.py` handles SmartAPI auth, `tokens.json` persistence, `fetch_historical_data()`, and `place_order()`.
  - `src/backtester.py` is the simulated execution engine. It accepts a `Strategy` implementation and iterates historical candles.
  - `src/live_trader.py` runs live polling and optional websocket-based `Ticker` updates, then executes signals through `SmartAPIClient`.
  - `src/strategy_interface.py` defines the contract: `on_tick()`, `on_data()`, `generate_signal()`.
  - `src/strategies/` contains strategy implementations; `src/strategy_factory.py` builds many `UniversalStrategy` combinations from base algos.

- Key patterns:
  - Strategies maintain internal candle buffers in `self.data_buffer` and support both dict and `pd.Series` input in `on_data()`.
  - `generate_signal()` may return a simple string (`BUY`/`SELL`/`HOLD`) or an option metadata dict for `Backtester`.
  - `UniversalStrategy` maps directional bias to execution modes like `EQUITY_INTRADAY`, `OPTION_BUY`, and `OPTION_SELL`.
  - `Backtester` supports separate signal and trade tokens, auto-square-off at 15:15, and Thursday option expiry.

- Important files/directories:
  - `config.json`: credentials, risk settings, capital allocation.
  - `tokens.json`: saved SmartAPI session tokens. `SmartAPIClient.login_via_browser()` uses manual browser URL paste and persists tokens here.
  - `data/historical/`: cached fetched candle CSVs.
  - `backtest_reports/`: saved per-symbol and bulk backtest reports.
  - `tests/test_e2e.py`: the existing test harness uses `unittest` and mocks the backtester flow.

- Run patterns:
  - Backtest: `python main.py --mode backtest --strategy momentum --token 3045 --symbol SBIN-EQ`
  - Live: `python main.py --mode live --strategy momentum --token 3045 --symbol SBIN-EQ --websocket`
  - Bulk backtest: `python scripts/bulk_backtest.py`
  - Verify websocket: `python verify_websocket.py`
  - Test suite: `python -m unittest tests/test_e2e.py`

- Project-specific conventions:
  - There is no `.env` loader in code; `config.json` is the actual credential/config source.
  - New strategies should implement `Strategy` and be imported in `src/strategies/__init__.py` to be available for CLI mapping.
  - `StrategyFactory.generate_strategies()` creates many algorithm-mode combos; keep legacy named strategies only when needed.
  - Logging uses `src/logger.py`: runtime orders/signals to `logs/YYYY-MM-DD/<strategy>/`, and exceptions to `error_reports/`.

- External dependencies:
  - `SmartApi` and `SmartApi.smartWebSocketV2` for broker API/websocket.
  - `pandas`, `requests`, `websocket-client`, and standard `json`, `datetime`, `argparse`.

Keep instructions tightly aligned with these file-level responsibilities and avoid suggesting generic project practices not already reflected in repository structure.