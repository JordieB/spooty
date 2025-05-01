import unittest
import logging
import os
from pathlib import Path
from spooty.utils.logging_setup import setup_logging, get_logger

class TestLogging(unittest.TestCase):
    def setUp(self):
        # Create temporary log directory
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        self.log_file = self.log_dir / "spooty.log"
        
        # Clear any existing handlers
        logging.getLogger().handlers.clear()
        
    def tearDown(self):
        # Clean up log files
        if self.log_file.exists():
            self.log_file.unlink()
        
    def test_logging_initialization(self):
        """Test that logging is properly initialized"""
        setup_logging()
        logger = get_logger("test")
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.level, logging.NOTSET)  # Logger itself should be NOTSET
        
        # Check root logger configuration
        root_logger = logging.getLogger()
        self.assertEqual(root_logger.level, logging.INFO)
        
        # Verify handlers are set up
        self.assertTrue(any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers))
        self.assertTrue(any(isinstance(h, logging.handlers.RotatingFileHandler) for h in root_logger.handlers))
        
    def test_log_file_creation(self):
        """Test that log files are created and written to"""
        logger = get_logger("test")
        test_message = "Test log message"
        logger.info(test_message)
        
        # Verify log file exists and contains the message
        self.assertTrue(self.log_file.exists())
        with open(self.log_file, 'r') as f:
            log_content = f.read()
            self.assertIn(test_message, log_content)
            
    def test_log_rotation(self):
        """Test that log rotation works"""
        logger = get_logger("test")
        
        # Write enough data to trigger rotation (5MB + 1 byte)
        data = "x" * 1024  # 1KB of data
        for _ in range(5 * 1024 + 1):  # Write 5MB + 1KB
            logger.info(data)
            
        # Check that rotation occurred
        self.assertTrue(self.log_file.exists())
        self.assertTrue(any(f.name.startswith("spooty.log.") for f in self.log_dir.iterdir()))
        
    def test_multiple_logger_instances(self):
        """Test that multiple logger instances work correctly"""
        logger1 = get_logger("test1")
        logger2 = get_logger("test2")
        
        test_message1 = "Test message 1"
        test_message2 = "Test message 2"
        
        logger1.info(test_message1)
        logger2.info(test_message2)
        
        with open(self.log_file, 'r') as f:
            log_content = f.read()
            self.assertIn(test_message1, log_content)
            self.assertIn(test_message2, log_content)
            
    def test_log_levels(self):
        """Test that different log levels work as expected"""
        logger = get_logger("test")
        
        # Log messages at different levels
        debug_msg = "Debug message"
        info_msg = "Info message"
        warning_msg = "Warning message"
        error_msg = "Error message"
        
        logger.debug(debug_msg)
        logger.info(info_msg)
        logger.warning(warning_msg)
        logger.error(error_msg)
        
        with open(self.log_file, 'r') as f:
            log_content = f.read()
            # DEBUG should not be present as we're using INFO level
            self.assertNotIn(debug_msg, log_content)
            # INFO and above should be present
            self.assertIn(info_msg, log_content)
            self.assertIn(warning_msg, log_content)
            self.assertIn(error_msg, log_content)

if __name__ == '__main__':
    unittest.main() 