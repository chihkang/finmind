import logging
from config.settings import LOG_LEVEL, LOG_FORMAT

def get_logger(name: str) -> logging.Logger:
    """配置並返回logger實例"""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(LOG_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    logger.setLevel(LOG_LEVEL)
    return logger