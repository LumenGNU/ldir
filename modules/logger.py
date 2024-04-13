import logging
import sys


def get_logger(name=__name__, level=logging.DEBUG, stream=sys.stderr):
    """Настроить и вернуть сконфигурированный логгер."""
    # Создание логгера
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Создание handler, который выводит сообщения на заданный поток
    handler = logging.StreamHandler(stream)
    handler.setLevel(level)

    # Создание и установка формата сообщений
    formatter = logging.Formatter("%(name)s - %(levelname)s: %(class)s/%(funcName)s: %(message)s")
    handler.setFormatter(formatter)

    # Добавление handler к логгеру, если он ещё не добавлен
    if not logger.handlers:
        logger.addHandler(handler)

    return logger
