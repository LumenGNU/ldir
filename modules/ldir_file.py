#!/usr/bin/env python3
"""
__file__ = ldir_file.py
"""

from __future__ import annotations
import os
from typing import Any, Dict, Final, Generator, Iterator, List, Optional, Tuple, Union


from modules.fs_elements import (
    RootDirectoryElement,
    FileElement,
    DirectoryElement,
)

from .GroupedString import GroupedString


class Field:
    """Представляет собой одно поле в Entry."""

    def __init__(self, index: int, value: str, level: int = 0, group="default") -> None:
        """Инициализирует объект Field."""
        self.__value: Final = value
        self.__index: Final = index
        self.__level: Final = level
        self.__group: Final = group

        self.__text: GroupedString

        if self.index == 0:  # marker
            self.__text = GroupedString(f"{self.value}:", "marker")
        elif self.index == 1:  # name
            self.__text = GroupedString(f"{'  ' * self.level}{self.__value}", f"{self.index}{self.group}")
        elif self.index == 2:  # extra_field1
            self.__text = GroupedString(f"| {self.value}", f"{self.index}{self.group}")
        else:  # extra_fieldN
            self.__text = GroupedString(f"; {self.value}", f"{self.index}{self.group}")

    @property
    def index(self):
        return self.__index

    @property
    def text(self):
        return self.__text

    @property
    def group(self):
        return self.__group

    @property
    def value(self) -> str:
        """Возвращает значение поля."""
        return self.__value

    @property
    def level(self) -> int:
        """Возвращает уровень вложенности."""
        return self.__level

    def __str__(self) -> GroupedString:
        """Возвращает строковое представление объекта."""
        return self.text


class Entry:
    """Представляет собой одну строку в файле и состоит из полей Field. Каждая такая строка
    ассоциирована с объектом FileElement или DirectoryElement.

    Строка в файле имеет следующий формат:

    ```
    <marker>: <name> [| <extra_field1> [; <extra_field2>] ...]
    ```
    """

    def __init__(self, element: FileElement | DirectoryElement) -> None:
        """Инициализирует объект Entry."""

        self.__element: Final = element

        self.__fields: Final[list[Field]]

    # def __iter__(self) -> Iterator[Field]:
    #     """Возвращает итератор по полям."""
    #     return iter(self.__fields)

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
        return self.__element.is_file

    def is_dir(self) -> bool:
        """Проверяет, является ли ."""
        return self.__element.is_dir

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
            if element.is_empty:
                group = element.parent.path
            else:
                group = element.path
        else:
            group = element.parent.path if element.parent else "root"

        index = -1
        # первые два обязательных поля
        # <marker>
        marker = "#" if element.immutable else str(element.inode)
        fields.append(Field(index := index + 1, marker, group="marker"))
        # <name>
        frmt_name: str = f"['{element.name}']" if element.is_dir else f"'{element.name}'"
        fields.append(Field(index := index + 1, frmt_name, level=element.level, group=group))

        # # @for_debug: for test
        # fields.append(Field(index := index + 1, str(element.level), group=group))
        # fields.append(Field(index := index + 1, group, group=group))
        # fields.append(Field(index := index + 1, "<extra1>", group=group))
        # fields.append(Field(index := index + 1, "<extra2>", group=group))

        return Entry(element.is_dir, group, fields)


class Data:
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
        last_l = -1
        for entry in self:
            # out += f"{entry.group} "
            if entry.is_dir():  # прижимать между собой пустые директории одного уровня
                if last_e or last_l != entry[1].level:
                    out += "\n"
                last_e = False
            else:
                last_e = True
            last_l = entry[1].level
            out += str(entry).rstrip() + "\n"
        return out


if __name__ == "__main__":
    pass
