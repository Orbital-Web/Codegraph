import logging
import sys

from colorama import Fore, Style
from colorama import init as colorama_init

from codegraph.configs.app_configs import LOG_LEVEL

_LEVEL_NAME_TO_VALUE: dict[str, int] = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
    "NOTSET": logging.NOTSET,
}

colorama_init()


class ColoredLogFormatter(logging.Formatter):

    LOG_COLORS = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Style.BRIGHT + Fore.RED,
    }

    def format(self, record: logging.LogRecord) -> str:
        levelname = f"{record.levelname:<8}"
        color = self.LOG_COLORS.get(record.levelno, "")
        record.coloredlevel = f"{color}{levelname}{Style.RESET_ALL}"
        return super().format(record)


def get_logger(name: str = __name__) -> logging.Logger:
    """Return a configured logger."""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    loglevel = _LEVEL_NAME_TO_VALUE.get(LOG_LEVEL, logging.INFO)
    logger.setLevel(loglevel)

    formatter = ColoredLogFormatter(
        fmt="%(coloredlevel)s  %(asctime)s  %(filename)24s  %(lineno)4d  %(message)s",
        datefmt="%m/%d/%Y %H:%M:%S",
    )

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setLevel(logger.level)
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.propagate = False

    return logger
