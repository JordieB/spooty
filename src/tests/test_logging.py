import unittest
import logging
import os
import time
from pathlib import Path
from spooty.utils.logging_setup import setup_logging, get_logger

class TestLogging(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Reset logging configuration
        logging.getLogger().handlers.clear()
        self._reset_logging_state()
        
        # Create temporary log directory
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        self.log_file = self.log_dir / "spooty.log"
        
        # Remove existing log files
        self._cleanup_log_files()
        
    def tearDown(self):
        """Clean up after each test method."""
        # Close all handlers to release file locks
        logging.shutdown()
        # Remove log files
        self._cleanup_log_files()
        
    def _cleanup_log_files(self):
        """Remove all log files in the log directory."""
        if self.log_dir.exists():
            for file in self.log_dir.glob("spooty.log*"):
                try:
                    file.unlink()
                except (PermissionError, OSError):
                    # If file is locked, wait briefly and try again
                    time.sleep(0.1)
                    try:
                        file.unlink()
                    except:
                        pass
                        
    def _reset_logging_state(self):
        """Reset the logging initialization state."""
        import spooty.utils.logging_setup as logging_setup
        logging_setup._logging_initialized = False
        
    def test_logging_initialization(self):
        """Test that logging is properly initialized."""
        setup_logging()
        logger = get_logger("test")
        
        # Verify logger is properly configured
        self.assertIsInstance(logger, logging.Logger)
        self.assertTrue(self.log_file.exists())
        
        # Get the actual logger instance that should have the handlers
        spooty_logger = logging.getLogger("spooty")
        self.assertTrue(any(isinstance(h, logging.handlers.RotatingFileHandler) 
                          for h in spooty_logger.handlers))
                          
    def test_log_levels(self):
        """Test that different log levels work correctly."""
        logger = get_logger("test")
        
        # Log messages at different levels
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        
        # Force handlers to flush
        for handler in logger.handlers:
            handler.flush()
            
        # Read log file contents
        with open(self.log_file, 'r') as f:
            log_content = f.read()
            
        # Verify log levels (INFO and above should be present)
        self.assertNotIn("Debug message", log_content)
        self.assertIn("Info message", log_content)
        self.assertIn("Warning message", log_content)
        self.assertIn("Error message", log_content)
        
    def test_multiple_logger_instances(self):
        """Test that multiple logger instances work correctly."""
        logger1 = get_logger("test1")
        logger2 = get_logger("test2")
        
        # Log messages from different loggers
        logger1.info("Test message 1")
        logger2.info("Test message 2")
        
        # Force handlers to flush
        spooty_logger = logging.getLogger("spooty")
        for handler in spooty_logger.handlers:
            handler.flush()
            
        # Read log file contents
        with open(self.log_file, 'r') as f:
            log_content = f.read()
            
        # Verify both messages are present
        self.assertIn("Test message 1", log_content)
        self.assertIn("Test message 2", log_content)
        
    def test_log_rotation(self):
        """Test that log rotation works correctly."""
        logger = get_logger("test")
        
        # Write enough data to trigger rotation (5MB per file)
        large_msg = "X" * 1024 * 1024  # 1MB message
        for _ in range(6):  # Should create at least one rotation
            logger.info(large_msg)
            
        # Force handlers to flush
        spooty_logger = logging.getLogger("spooty")
        for handler in spooty_logger.handlers:
            handler.flush()
            
        # Verify rotation occurred
        rotation_files = list(self.log_dir.glob("spooty.log.*"))
        self.assertGreater(len(rotation_files), 0)
        
    def test_log_file_creation(self):
        """Test that log files are created in the correct location."""
        logger = get_logger("test")
        logger.info("Test message")
        
        # Force handlers to flush
        spooty_logger = logging.getLogger("spooty")
        for handler in spooty_logger.handlers:
            handler.flush()
            
        # Verify log file exists and contains the message
        self.assertTrue(self.log_file.exists())
        with open(self.log_file, 'r') as f:
            self.assertIn("Test message", f.read())

if __name__ == '__main__':
    unittest.main() 