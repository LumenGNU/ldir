#!/usr/bin/env python3
""""""

from __future__ import annotations
from operator import attrgetter
import os
from typing import Any, Literal, Never, Optional, Tuple, Union
import magic

from modules.protocols import SortTypeLiteral

magic_obj: Optional[magic.Magic] = None


def sort_method(method: SortTypeLiteral) -> Any:
    return globals()[f"sort_{method}_method"]


def sort_none_method(element: Any) -> bool:
    return False


def sort_iname_method(element: Any) -> str:
    """
    Сортировать элементы по атрибуту `name` без учета регистра.
    """
    return getattr(element, "name", "_").lower()


def sort_name_method(element: Any) -> str:
    """
    Сортировать элементы по атрибуту `name` с учетом регистра.
    """
    return getattr(element, "name", "_")


def sort_type_method(element: Any) -> Tuple[str, str]:
    """Сортировать элементы по атрибуту `extension`. Элементы без атрибута располагаются выше остальных."""
    return getattr(element, "extension", ""), getattr(element, "name", "_").lower()


def sort_mime_method(element: Any) -> Tuple[str, str]:
    """Сортирует элементы по MIME"""
    # Файлы без MIME возвращают ("\0", имя), что поместит их выше файлов с MIME
    # Создаём объект Magic
    global magic_obj
    if magic_obj is None:
        magic_obj = magic.Magic(mime=True)
    # Определяем тип файла
    file_type = magic_obj.from_file(getattr(element, "path"))
    return file_type, getattr(element, "name", "_").lower()


if __name__ == "__main__":
    pass
