# app/utils/logger_util.py
from app.infrastructure.logging.logger import LoggerFactory


def get_logger(module_name: str):
    """
    Get a logger for the specified module.

    Args:
        module_name: Name of the module, typically use __name__

    Returns:
        Configured logger instance
    """
    LoggerFactory.setup_logging()
    return LoggerFactory.get_logger(module_name)