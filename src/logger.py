import os
import datetime
import traceback
import logging

ERROR_DIR = "error_reports"
LOG_DIR = "logs"

class SystemLogger:
    @staticmethod
    def log_error(exception, context_message="An error occurred"):
        """
        Logs an exception to a timestamped file in the error_reports directory.
        """
        try:
            if not os.path.exists(ERROR_DIR):
                os.makedirs(ERROR_DIR)
            
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"error_{timestamp}_{id(exception)}.txt"
            filepath = os.path.join(ERROR_DIR, filename)
            
            with open(filepath, "w") as f:
                f.write(f"Context: {context_message}\n")
                f.write(f"Timestamp: {timestamp}\n")
                f.write(f"Exception Type: {type(exception).__name__}\n")
                f.write(f"Exception Message: {str(exception)}\n")
                f.write("-" * 50 + "\n")
                f.write("Traceback:\n")
                f.write(traceback.format_exc())
                
            print(f"Error logged to {filepath}")
        except Exception as e:
            print(f"CRITICAL: Failed to log error: {e}")
            traceback.print_exc()

# Backwards compatibility alias
log_error = SystemLogger.log_error

class TradeLogger:
    def __init__(self, strategy_name):
        self.strategy_name = strategy_name
        self.date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        self.base_path = os.path.join(LOG_DIR, self.date_str, self.strategy_name)
        
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path)
            
        self.data_logger = self._setup_logger("data", os.path.join(self.base_path, "data.log"))
        self.signal_logger = self._setup_logger("signals", os.path.join(self.base_path, "signals.log"))
        self.order_logger = self._setup_logger("orders", os.path.join(self.base_path, "orders.log"))

    def _setup_logger(self, name, log_file):
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler = logging.FileHandler(log_file)
        handler.setFormatter(formatter)
        
        logger = logging.getLogger(f"{self.strategy_name}_{name}")
        logger.setLevel(logging.INFO)
        # Avoid adding multiple handlers if logger already exists
        if not logger.handlers:
            logger.addHandler(handler)
            
        return logger

    def log_data(self, message):
        self.data_logger.info(message)

    def log_signal(self, message):
        self.signal_logger.info(message)

    def log_order(self, message):
        self.order_logger.info(message)
        print(f"ORDER LOGGED: {message}") # Also print to console

