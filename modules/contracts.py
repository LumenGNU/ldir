#!/usr/bin/env python3
""""""

from functools import wraps
import os
from typing import Callable, Optional, Any, TypeVar, ParamSpec


class ContractPreconditionError(ValueError):
    """Исключение, возникающее при нарушении предусловия."""

    def __init__(self, obj: Any, message: str) -> None:
        super().__init__(f"{obj.__module__}: {obj.__class__.__name__}:\n\t{message}")


P = ParamSpec("P")
R = TypeVar("R")


def contract(
    pre_condition: Callable[..., Any], post_condition: Optional[Callable[[Any], Any]] = None, /
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Декоратор, применяющий контракты к функции.

    Args:
        pre_condition: Функция предусловия, принимает те же аргументы, что и целевая функция.
        post_condition: Функция постусловия, принимает результат выполнения функции (необязательно).

    Returns:
        Обернутая функция с контрактами.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Проверка предусловия
            pre_condition(*args, **kwargs)
            result = func(*args, **kwargs)
            # Проверка постусловия, если оно задано
            if post_condition:
                post_condition(result)
            return result

        return wrapper

    return decorator


def has_valid_dir_path(*args, **kwargs) -> None:
    """Проверяет, что позиционный или ключевой параметр `path` — это путь, что он существует и является директорией."""
    # Извлекает параметр 'path' из kwargs или args[0]
    path = kwargs.get("path") or (args[0] if args else None)

    # Проверяет, что path предоставлен и является директорией
    if path is None or not os.path.isdir(path):
        raise ContractPreconditionError(path, f"Указанный путь не существует, или не является директорией: {path}")


if __name__ == "__main__":
    pass
