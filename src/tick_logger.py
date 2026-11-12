import os
import csv
from datetime import datetime
from .logger import log_error

class TickLogger:
    def __init__(self, base_dir="data/ticks"):
        """
        Initializes the Tick Logger.
        
        :param base_dir: Directory where tick files will be saved.
        """
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        self.files = {} # (token, date) -> file object
        self.writers = {} # (token, date) -> csv writer

    def _get_file_and_writer(self, token):
        date_str = datetime.now().strftime("%Y-%m-%d")
        key = (token, date_str)
        
        if key not in self.files:
            file_path = os.path.join(self.base_dir, f"ticks_{token}_{date_str}.csv")
            file_exists = os.path.exists(file_path)
            
            f = open(file_path, "a", newline="")
            writer = csv.writer(f)
            
            if not file_exists:
                # Write header
                writer.writerow([
                    "exchange_timestamp", "last_traded_price", "sequence_number", 
                    "subscription_mode", "exchange_type"
                ])
            
            self.files[key] = f
            self.writers[key] = writer
            
        return self.writers[key]

    def log_tick(self, tick_data):
        """
        Logs a single tick to the appropriate file.
        """
        try:
            token = tick_data.get("token")
            if not token:
                return

            writer = self._get_file_and_writer(token)
            writer.writerow([
                tick_data.get("exchange_timestamp"),
                tick_data.get("last_traded_price"),
                tick_data.get("sequence_number"),
                tick_data.get("subscription_mode"),
                tick_data.get("exchange_type")
            ])
            # For data safety, periodic flushing might be needed, 
            # but standard file buffering is usually fine for this volume.
        except Exception as e:
            print(f"Error in TickLogger.log_tick: {e}")
            log_error(e, "TickLogger.log_tick")

    def close(self):
        """Closes all open file handles."""
        for f in self.files.values():
            f.close()
        self.files.clear()
        self.writers.clear()
