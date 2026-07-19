import os
from pathlib import Path
from dotenv import load_dotenv, set_key

class Settings:
    """Manages application settings and configuration stored in .env and ensures required directories exist."""
    
    def __init__(self, base_dir: Path = None):
        if base_dir is None:
            self.base_dir = Path(__file__).resolve().parent
        else:
            self.base_dir = Path(base_dir)
            
        self.env_path = self.base_dir / ".env"
        
        # Ensure directories exist
        self.ensure_directories()
        
        # Load environment variables
        self.load()
        
    def ensure_directories(self) -> None:
        """Create necessary project subdirectories if they do not exist."""
        directories = ["templates", "logs", "reports", "assets"]
        for directory in directories:
            (self.base_dir / directory).mkdir(parents=True, exist_ok=True)
            
    def load(self) -> None:
        """Loads or reloads configuration from the .env file."""
        if not self.env_path.exists():
            # Create a default .env file if it doesn't exist
            with open(self.env_path, "w", encoding="utf-8") as f:
                f.write(
                    "# WhatsApp Business Cloud API Configuration\n"
                    "ACCESS_TOKEN=your_whatsapp_access_token_here\n"
                    "PHONE_NUMBER_ID=your_phone_number_id_here\n"
                    "API_VERSION=v20.0\n"
                    "CONNECTION_METHOD=api\n\n"
                    "# Application Preferences\n"
                    "APP_THEME=System\n"
                    "SENDER_DELAY=5\n"
                    "RETRY_LIMIT=3\n"
                    "PLAY_SOUND=True\n"
                )
        
        # Load env into system variables
        load_dotenv(self.env_path, override=True)
        
        # WhatsApp API Configuration
        self.access_token = os.getenv("ACCESS_TOKEN", "")
        self.phone_number_id = os.getenv("PHONE_NUMBER_ID", "")
        self.api_version = os.getenv("API_VERSION", "v20.0")
        self.connection_method = os.getenv("CONNECTION_METHOD", "api")
        
        # Application Preferences
        self.app_theme = os.getenv("APP_THEME", "System")
        
        try:
            self.sender_delay = int(os.getenv("SENDER_DELAY", "5"))
        except ValueError:
            self.sender_delay = 5
            
        try:
            self.retry_limit = int(os.getenv("RETRY_LIMIT", "3"))
        except ValueError:
            self.retry_limit = 3
            
        self.play_sound = os.getenv("PLAY_SOUND", "True").lower() == "true"

    def save(self, 
             access_token: str = None, 
             phone_number_id: str = None, 
             api_version: str = None, 
             app_theme: str = None, 
             sender_delay: int = None, 
             retry_limit: int = None, 
             play_sound: bool = None,
             connection_method: str = None) -> None:
        """Saves configuration changes to the .env file and updates memory attributes."""
        
        # Create file if missing
        if not self.env_path.exists():
            self.load()
            
        if access_token is not None:
            self.access_token = access_token.strip()
            set_key(str(self.env_path), "ACCESS_TOKEN", self.access_token)
            
        if phone_number_id is not None:
            self.phone_number_id = phone_number_id.strip()
            set_key(str(self.env_path), "PHONE_NUMBER_ID", self.phone_number_id)
            
        if api_version is not None:
            self.api_version = api_version.strip()
            set_key(str(self.env_path), "API_VERSION", self.api_version)
            
        if app_theme is not None:
            self.app_theme = app_theme.strip()
            set_key(str(self.env_path), "APP_THEME", self.app_theme)
            
        if sender_delay is not None:
            self.sender_delay = sender_delay
            set_key(str(self.env_path), "SENDER_DELAY", str(self.sender_delay))
            
        if retry_limit is not None:
            self.retry_limit = retry_limit
            set_key(str(self.env_path), "RETRY_LIMIT", str(self.retry_limit))
            
        if play_sound is not None:
            self.play_sound = play_sound
            set_key(str(self.env_path), "PLAY_SOUND", str(self.play_sound))
            
        if connection_method is not None:
            self.connection_method = connection_method.strip().lower()
            set_key(str(self.env_path), "CONNECTION_METHOD", self.connection_method)
            
        # Re-load to confirm alignment
        self.load()
