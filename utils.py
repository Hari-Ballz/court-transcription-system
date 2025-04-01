import logging
import os
from datetime import datetime

def create_logger(name: str) -> logging.Logger:
    """
    Create a logger with the given name
    
    Args:
        name: Logger name
    
    Returns:
        Configured logger
    """
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Create file handler
    file_handler = logging.FileHandler(f"logs/{name}.log")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

def generate_timestamp() -> str:
    """
    Generate a formatted timestamp
    
    Returns:
        Current timestamp string
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")