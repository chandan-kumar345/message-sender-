import logging
from pathlib import Path
import csv
from datetime import datetime
import pandas as pd
from typing import Optional

class WhatsAppLogger:
    """Manages application debugging logs and recording campaign send logs in CSV with Excel export capability."""
    
    def __init__(self, base_dir: Path = None):
        if base_dir is None:
            self.base_dir = Path(__file__).resolve().parent
        else:
            self.base_dir = Path(base_dir)
            
        self.logs_dir = self.base_dir / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        self.app_log_path = self.logs_dir / "app.log"
        self.history_csv_path = self.logs_dir / "whatsapp_send_history.csv"
        
        # Setup application-wide logging
        self._setup_app_logger()
        # Initialize campaign history file
        self._init_history_csv()

    def _setup_app_logger(self) -> None:
        """Sets up python standard logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            handlers=[
                logging.FileHandler(self.app_log_path, encoding="utf-8"),
                logging.StreamHandler()
            ]
        )

    def _init_history_csv(self) -> None:
        """Creates the WhatsApp send history CSV file and writes headers if it doesn't exist."""
        headers = ["Timestamp", "Lead Name", "Phone Number", "Message Preview", "Status", "WhatsApp Message ID", "Error Details"]
        if not self.history_csv_path.exists():
            try:
                with open(self.history_csv_path, mode="w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(headers)
            except Exception as e:
                logging.error(f"Failed to initialize WhatsApp sending history CSV: {e}")

    def log_transmission(self, 
                         lead_name: str, 
                         phone_number: str, 
                         message: str, 
                         status: str, 
                         whatsapp_id: Optional[str] = "", 
                         error_msg: Optional[str] = "") -> None:
        """
        Appends a message send result row to the history CSV file.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Truncate message for preview in logs if too long (e.g. keep first 100 chars)
        msg_preview = message.replace("\n", " ")[:100]
        if len(message) > 100:
            msg_preview += "..."
            
        row = [
            timestamp,
            lead_name,
            phone_number,
            msg_preview,
            status,
            whatsapp_id or "",
            error_msg or ""
        ]
        
        try:
            with open(self.history_csv_path, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(row)
            logging.info(f"Log stored: {phone_number} | {status} | Error: {error_msg}")
        except Exception as e:
            logging.error(f"Failed to write sending log to CSV: {e}")

    def get_history_df(self) -> pd.DataFrame:
        """Reads the history CSV and returns it as a pandas DataFrame."""
        if not self.history_csv_path.exists():
            self._init_history_csv()
        try:
            return pd.read_csv(self.history_csv_path)
        except Exception as e:
            logging.error(f"Error reading history CSV: {e}")
            return pd.DataFrame()

    def export_history_to_excel(self, export_path: str) -> bool:
        """
        Reads sending logs from CSV and exports them to an Excel file.
        """
        try:
            df = self.get_history_df()
            if df.empty:
                logging.warning("No campaign history logs found to export.")
                return False
                
            export_path_obj = Path(export_path)
            export_path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            df.to_excel(export_path, index=False, sheet_name="WhatsApp Dispatch Logs")
            logging.info(f"Exported send history to {export_path}")
            return True
        except Exception as e:
            logging.error(f"Failed to export log history to Excel: {e}")
            return False
