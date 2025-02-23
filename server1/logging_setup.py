

import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime
import pytz  # Ensure you have `pytz` installed: pip install pytz

IST = pytz.timezone('Asia/Kolkata')

class ISTFormatter(logging.Formatter):
    """Custom formatter to use Indian Standard Time (IST) in logs."""
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, IST)
        return dt.strftime(datefmt or "%Y-%m-%d %H:%M:%S")

class LoggerHandler:
    """
    Create Logger file handler with the ability to store logs in separate fi    les for each level
    and ensure log rotation based on size limits only.
    """
    LogDir = os.path.join(os.path.dirname(__file__), "logs")  # Logs folder inside the hlx_dtp_api folder

    def __init__(self):
        self.handlers = {}  # Store handlers to ensure reusability of loggers
        # Ensure that the 'logs' directory exists
        if not os.path.exists(self.LogDir):
            os.makedirs(self.LogDir)

    def get_logger(self, file_name=__name__, level=None):
        """
        Get the logger and its level update/set and return the result.
        :param file_name: present working file
        :param level: DEBUG, INFO, WARNING, ERROR, CRITICAL
        :return: logger object
        """
        # Create a unique logger for each level
        logger = logging.getLogger(f"{file_name}_{level}")  # Use level to create unique logger names

        # Only set the level if it's not already set
        if not logger.hasHandlers():
            logger.setLevel(self.get_log_level(level))

        return logger

    def set_formatter(self, level=None):
        """
        Set the logger file format and its level.
        :param level: DEBUG, INFO, WARNING, ERROR, CRITICAL
        :return: file handler and formatter
        """
        formatter = ISTFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # Set different log files for different levels
        log_file = self.get_log_file(level)
        rotating_handler = self.get_rotating_file_handler(log_file, level)
        rotating_handler.setLevel(self.get_log_level(level))
        rotating_handler.setFormatter(formatter)

        return rotating_handler, formatter

    def stream_handler(self, formatter=None):
        """
        Handle the stream values and format the file and return the result.
        :param formatter: The formatter to be used for the stream handler
        :return: stream_handler
        """
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.DEBUG)  # Set this to DEBUG to show all levels in console
        stream_handler.setFormatter(formatter)
        return stream_handler

    def add_handler(self, logger=None, handler=None):
        """
        Add the log handler to the logger.
        :param logger: The logger to which the handler will be added
        :param handler: The handler to be added
        """
        # Avoid adding duplicate handlers
        if not any(isinstance(h, type(handler)) for h in logger.handlers):
            logger.addHandler(handler)

    def get_log_level(self, level):
        """
        Return the appropriate logging level.
        :param level: Log level string (DEBUG, INFO, etc.)
        :return: Corresponding log level from the logging module
        """
        levels = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        return levels.get(level.upper(), logging.INFO)

    def get_log_file(self, level):
        """
        Return the log file name based on the log level.
        :param level: Log level string (DEBUG, INFO, etc.)
        :return: File name for the log file
        """
        log_files = {
            "DEBUG": "debug.log",
            "INFO": "info.log",
            "WARNING": "warning.log",
            "ERROR": "error.log",
            "CRITICAL": "critical.log"
        }

        return os.path.join(self.LogDir, log_files.get(level.upper(), "application.log"))

    def get_rotating_file_handler(self, log_file, level):
        """
        Create a handler that rotates the log file based on size.
        :param log_file: The log file name
        :param level: The log level
        :return: A handler that handles size-based rotation
        """
        max_log_size = 30 * 1024 * 1024  # 30MB in bytes
        backup_count = 5  # Keep the last 5 backup files

        # Create size-based rotating handler (RotatingFileHandler)
        rotating_handler = RotatingFileHandler(
            log_file, maxBytes=max_log_size, backupCount=backup_count
        )

        return rotating_handler


def logger_level(level, filename=__name__):
    """
    Create a logger for a given level and return the result.
    :param level: Logging level as string (DEBUG, INFO, etc.)
    :param filename: File name to use for logger (default is the script's name)
    :return: logger object
    """
    logger_obj = LoggerHandler()

    # Get logger object with appropriate level
    logger = logger_obj.get_logger(file_name=filename, level=level)

    # Set up formatter and handlers
    rotating_handler, formatter = logger_obj.set_formatter(level=level)
    stream_handler = logger_obj.stream_handler(formatter=formatter)

    # Add handlers to the logger
    logger_obj.add_handler(logger, rotating_handler)
    logger_obj.add_handler(logger, stream_handler)

    return logger

if __name__ == "__main__":
    # Create loggers for each level
    logger_debug = logger_level("DEBUG")
    logger_info = logger_level("INFO")
    logger_warning = logger_level("WARNING")
    logger_error = logger_level("ERROR")
    logger_critical = logger_level("CRITICAL")

    # Log messages at different levels
    logger_info.info("Logging data at INFO level!")
    logger_debug.debug("Logging data at DEBUG level!")
    logger_warning.warning("Logging data at WARNING level!")
    logger_error.error("Logging data at ERROR level!")
    logger_critical.critical("Logging data at CRITICAL level!")
