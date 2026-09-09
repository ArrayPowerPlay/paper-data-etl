import logging
import sys
import os

def setup_logger(name: str) -> logging.Logger:
    """
    Setup a logger that outputs to both console and file.
    All files in the project should import this function.
    """
    logger = logging.getLogger(name)
    
    # If logger is already configured, return it to prevent duplicate logs
    if logger.hasHandlers():
        return logger
        
    logger.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Console Handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    # File Handler
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # We use a general app.log for all module logs
    fh = logging.FileHandler(os.path.join(log_dir, "app.log"), encoding='utf-8')
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    return logger
