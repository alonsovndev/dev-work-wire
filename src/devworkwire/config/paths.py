import os
from pathlib import Path


class Paths:
    """
    A centralized class for managing all application paths.
    Ensures portability and consistency across different environments.
    """

    # Base directory of the project
    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

    # Configuration directory
    CONFIG_DIR = BASE_DIR / "src/devworkwire/config"

    # Environment file path
    ENV_FILE_PATH = BASE_DIR / ".env"

    # Logs directory (if applicable)
    LOGS_DIR = BASE_DIR / "logs"

    # Local storage directory for files (if applicable)
    LOCAL_STORAGE_DIR = BASE_DIR / "../tmp/"

    @staticmethod
    def ensure_directories_exist():
        """
        Ensures that required directories (like logs or local storage) exist.
        Creates them if they are missing.
        """
        required_dirs = [Paths.LOGS_DIR, Paths.LOCAL_STORAGE_DIR]
        for directory in required_dirs:
            os.makedirs(directory, exist_ok=True)
