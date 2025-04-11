# app/infrastructure/logging/logger.py
import logging
import logging.config
import os
from typing import Optional, Dict, Any
import json

try:
    import colorlog
except ImportError:
    colorlog = None  # Graceful fallback if colorlog isn't installed


class LoggerFactory:
    """Factory for creating and configuring loggers."""

    _LOG_LEVELS = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL
    }

    @classmethod
    def setup_logging(cls,
                      config: Optional[Dict[str, Any]] = None,
                      config_path: Optional[str] = None,
                      default_level: str = "info",
                      log_format: Optional[str] = None) -> None:
        """
        Setup logging configuration from a dictionary, JSON file or defaults.
        """
        if config:
            logging.config.dictConfig(config)
        elif config_path and os.path.exists(config_path):
            with open(config_path, 'rt') as f:
                config = json.load(f)
            logging.config.dictConfig(config)
        else:
            level = cls._LOG_LEVELS.get(default_level.lower(), logging.INFO)

            if colorlog:
                handler = colorlog.StreamHandler()
                formatter = colorlog.ColoredFormatter(
                    "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    datefmt='%Y-%m-%d %H:%M:%S',
                    log_colors={
                        'DEBUG': 'cyan',
                        'INFO': 'green',
                        'WARNING': 'yellow',
                        'ERROR': 'red',
                        'CRITICAL': 'bold_red',
                    }
                )
                handler.setFormatter(formatter)
                root_logger = logging.getLogger()
                root_logger.setLevel(level)
                root_logger.handlers = []  # Clear default handlers
                root_logger.addHandler(handler)
            else:
                # Fallback to basicConfig if colorlog isn't available
                if not log_format:
                    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                logging.basicConfig(level=level, format=log_format, datefmt='%Y-%m-%d %H:%M:%S')

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get a logger with the specified name.

        Args:
            name: Logger name, typically the module name

        Returns:
            Configured logger instance
        """

        return logging.getLogger(name)