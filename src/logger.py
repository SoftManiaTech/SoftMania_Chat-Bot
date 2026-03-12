import logging
import sys

def setup_logger(name: str) -> logging.Logger:
    """Sets up a standardized logger for the application."""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Create console handler with format
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
    return logger
