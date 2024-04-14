#!/usr/bin/env python3
"""
__file__ = ldir_file.py
"""

from __future__ import annotations
import os
from typing import Any, Dict, Generator, Iterator, List, Optional, Tuple, Union

from modules.fs_elements import DirEntryProtocol

from .fs_elements import (
    DirEntryProtocol,
    RootDirectoryElement,
    FileElement,
    DirectoryElement,
    FileSystemElement,
)

from .sstring import SString


class Field:
    """Представляет собой одно поле в Entry."""

    def __init__(self, index: int, value: str, level: int = 0, group="default") -> None:
        """Инициализирует объект Field."""
        self.__value = value
        self.__index = index
        self.__level = level
        self.__group = group

        self.__text: SString

        if self.index == 0:  # marker
            self.__text = SString(f"{self.__value}:", group="marker")
        elif self.index == 1:  # name
            self.__text = SString(f"{'  ' * self.__level}{self.__value}", f"{self.__index}{self.__group}")
        elif self.index == 2:  # extra_field1
            self.__text = SString(f"| {self.__value}", f"{self.__index}{self.__group}")
        else:
            self.__text = SString(f"; {self.__value}", f"{self.__index}{self.__group}")

    @property
    def index(self):
        return self.__index

    @property
    def text(self):
        return self.__text

    @property
    def value(self) -> str:
        """Возвращает значение поля."""
        return self.__value

    def __str__(self) -> SString:
        """Возвращает строковое представление объекта."""
        return self.text


class Entry:
    """Представляет собой одну строку в файле. Состоит из полей Field.

    Строка в файле имеет следующий формат:
    <marker>: <name> [| <extra_field1> [; <extra_field2>] ...]
    """

    def __init__(self, is_dir: bool, group: str, fields: List[Field]) -> None:
        """Инициализирует объект Entry."""
        self.__fields = fields
        self.__is_file = not is_dir
        self.__is_dir = is_dir
        self.__group = group

    def __iter__(self) -> Iterator[Field]:
        """Возвращает итератор по полям."""
        return iter(self.__fields)

    def __getitem__(self, index: int) -> Field:
        """Возвращает поле по индексу."""
        return self.__fields[index]

    def __len__(self) -> int:
        """Возвращает количество полей."""
        return len(self.__fields)

    def __str__(self) -> str:
        """Возвращает строковое представление объекта."""
        out = ""
        for field in self:
            if field.index == 0:
                out += field.text.rjust(field.text.max_length)
            else:
                out += field.text.ljust(field.text.max_length)
            out += " "
        return out

    def is_file(self) -> bool:
        """Проверяет, является ли ."""
        return self.__is_file

    def is_dir(self) -> bool:
        """Проверяет, является ли ."""
        return self.__is_dir

    @property
    def group(self):
        return self.__group

    @staticmethod
    def create_from_element(element: Union[FileElement, DirectoryElement], **config: Any) -> Entry:
        """Создает Entry из элемента фс."""
        # Пример реализации, детали зависят от вашей структуры данных
        # @todo: реализовать
        fields: List[Field] = []

        group = ""
        if element.is_dir and config["depth"]:
            group = element.path
        else:
            group = element.parent.path if element.parent else "root"

        index = -1
        # первые два обязательных поля
        # <marker>

        marker = "#" if element.immutable else str(element.inode)
        fields.append(Field(index := index + 1, marker, group=group))
        # <name>
        frmt_name: str = f"['{element.name}']" if element.is_dir else f"'{element.name}'"
        fields.append(Field(index := index + 1, frmt_name, level=element.level, group=group))

        # # @for_debug: for test
        # fields.append(Field(index := index + 1, "<extra1>", group=group))
        # fields.append(Field(index := index + 1, "<extra2>", group=group))

        return Entry(element.is_dir, group, fields)


class LdirData:
    """LdirData class for the LdirFile class, представляет собой список строк в файле. Состоит из объектов Entry."""

    def __init__(self, path: str, **config: Any) -> None:
        """
        Инициализирует объект LdirData, загружая элементы из указанной директории.

        Args:
        `path` (str): Путь к директории.
        `**config`: Дополнительные параметры
        - обхода дерева:
            - `depth`: `int`
            - `subdirectories`: `bool`
            - `hidden`: `bool`
        """
        self.root_element = RootDirectoryElement(path, **config)

        self.__entries: Dict[int, Entry] = {}

        for element in self.root_element:
            if element is not None:
                self.__entries[element.inode] = Entry.create_from_element(element, **config)

    def __iter__(self) -> Iterator[Entry]:
        """
        Возвращает итератор по списку записей.

        Returns:
        Iterator[Entry]: Итератор по объектам Entry.
        """
        return iter(self.__entries.values())

    def __getitem__(self, index: int) -> Optional[Entry]:
        """
        Возвращает объект Entry по иноду.

        Args:
        index (int): Индекс объекта.

        Returns:
        Entry: Объект Entry.
        """
        return self.__entries.get(index, None)

    def __len__(self) -> int:
        """
        Возвращает количество записей.

        Returns:
        int: Количество записей.
        """
        return len(self.__entries)

    def __str__(self) -> str:
        """
        Возвращает строковое представление объекта.

        Returns:
        str: Строковое представление объекта.
        """
        out = ""
        last_e = True
        for entry in self:
            # out += f"{entry.group} "
            if entry.is_dir():
                if last_e:
                    out += "\n"
                last_e = False
            else:
                last_e = True
            out += str(entry).rstrip() + "\n"
        return out


if __name__ == "__main__":
    pass
