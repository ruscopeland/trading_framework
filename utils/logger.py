# utils/logger.py
import logging
from logging.handlers import RotatingFileHandler
import sys
from pathlib import Path
from typing import Optional
import os

class TradingLogger:
    """Custom logger for the trading system"""
    
    def __init__(self):
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        
        # Main log file
        self.main_log = self.log_dir / "trading_system.log"
        # Error log file
        self.error_log = self.log_dir / "error.log"
        # Trade log file
        self.trade_log = self.log_dir / "trades.log"
        
        # Initialize loggers
        self.main_logger = self._setup_logger("TradingSystem", self.main_log)
        self.error_logger = self._setup_logger("ErrorLog", self.error_log, level=logging.ERROR)
        self.trade_logger = self._setup_logger("TradeLog", self.trade_log)

    def _setup_logger(
        self, 
        name: str, 
        log_file: Path, 
        level: int = logging.INFO,
        max_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5
    ) -> logging.Logger:
        """Setup individual logger"""
        logger = logging.getLogger(name)
        logger.setLevel(level)
        
        # File handler with rotation
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_size,
            backupCount=backup_count
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger

    def log_trade(self, trade_data: dict):
        """Log trade information"""
        self.trade_logger.info(f"TRADE: {trade_data}")

    def log_error(self, error_msg: str, exc_info: Optional[Exception] = None):
        """Log error information"""
        if exc_info:
            self.error_logger.error(error_msg, exc_info=True)
        else:
            self.error_logger.error(error_msg)

    def log_info(self, msg: str):
        """Log general information"""
        self.main_logger.info(msg)

    def log_warning(self, msg: str):
        """Log warning information"""
        self.main_logger.warning(msg)

    def log_debug(self, msg: str):
        """Log debug information"""
        self.main_logger.debug(msg)

# Global logger instance
trading_logger = TradingLogger()
