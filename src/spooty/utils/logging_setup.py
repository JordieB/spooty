import os
import logging
import logging.config
from pathlib import Path

def setup_logging():
    """
    Set up logging configuration for the application.
    Creates the logs directory if it doesn't exist and configures logging.
    """
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Load logging configuration
    try:
        logging.config.fileConfig('logging.conf', disable_existing_loggers=False)
        logging.info("Logging setup completed successfully")
    except Exception as e:
        # Fallback configuration if loading fails
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        logging.error(f"Error setting up logging configuration: {str(e)}")

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name (str): Name for the logger, typically __name__ of the module
        
    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name) 