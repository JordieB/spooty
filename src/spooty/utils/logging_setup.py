import os
import logging
import logging.config
from pathlib import Path

# Global flag to track if logging has been initialized
_logging_initialized = False

def setup_logging():
    """
    Set up logging configuration for the application.
    Creates the logs directory if it doesn't exist and configures logging.
    Will only initialize logging once, even if called multiple times.
    """
    global _logging_initialized
    
    # Skip if already initialized
    if _logging_initialized:
        return
        
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Load logging configuration
    try:
        logging.config.fileConfig('logging.conf', disable_existing_loggers=False)
        logging.info("Logging setup completed successfully")
        _logging_initialized = True
    except Exception as e:
        # Fallback configuration if loading fails
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        logging.error(f"Error setting up logging configuration: {str(e)}")
        _logging_initialized = True

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    Ensures logging is initialized before returning the logger.
    
    Args:
        name (str): Name for the logger, typically __name__ of the module
        
    Returns:
        logging.Logger: Configured logger instance
    """
    # Ensure logging is initialized
    setup_logging()
    
    # Get logger with the spooty prefix to ensure proper handler configuration
    logger_name = f"spooty.{name}" if not name.startswith("spooty") else name
    return logging.getLogger(logger_name) 