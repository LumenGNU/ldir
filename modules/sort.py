#!/usr/bin/env python3
""""""

from __future__ import annotations
from operator import attrgetter
import os
from typing import Any, Literal, Optional, Tuple, Union
import magic

magic_obj: Optional[magic.Magic] = None


def sort_method(
    method: Literal[
        "name",
        "type",
        "mime",
    ],
) -> Any:
    return globals()[f"sort_{method}_method"]


def sort_name_method(element: Any) -> Tuple[bool, str]:
    """Сортирует элементы так, чтобы непустые директории оказались выше пустых. Для файлов используется сортировка по имени."""
    # Пустые директории будут возвращать (True, имя), что поместит их ниже непустых (False, имя)
    return getattr(element, "is_empty", False), getattr(element, "name", "_")


def sort_type_method(element: Any) -> Tuple[str, str]:
    """Сортирует элементы по расширению файла. Файлы без расширения располагаются выше файлов с расширением."""
    # Файлы без расширения возвращают ("\0", имя), что поместит их выше файлов с расширением
    return getattr(element, "ext", "\0"), getattr(element, "name", "_")


def sort_mime_method(element: Any) -> Tuple[str, str]:
    """Сортирует элементы по MIME"""
    # Файлы без MIME возвращают ("\0", имя), что поместит их выше файлов с MIME
    # Создаём объект Magic
    global magic_obj
    if magic_obj is None:
        magic_obj = magic.Magic(mime=True)
    # Определяем тип файла
    file_type = magic_obj.from_file(getattr(element, "path"))
    return file_type, getattr(element, "name", "_")


if __name__ == "__main__":
    pass
