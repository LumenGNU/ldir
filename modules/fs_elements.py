#!/usr/bin/env python3
"""
__file__ = "fs_elements.py"


Модуль fs_elements содержит реализацию классов для работы с элементами файловой системы.

Основные классы:

- FileSystemElement - абстрактный класс, описывающий элемент файловой системы, производный от DirEntryProtocol.
- FileElement и DirectoryElement - конкретные реализации для работы с файлами и директориями.
- RootDirectoryElement - класс, представляющий корневую директорию.

Эти классы позволяют получить информацию о файлах и директориях, а также обойти файловую систему
 и вывести ее содержимое в виде дерева.

Модуль fs_elements предназначен для представления и взаимодействия с элементами
файловой системы. Он содержит классы, моделирующие файлы и директории, и
предоставляет методы для получения информации о них, такие как имя, путь и тип.

Этот модуль также предоставляет функциональность для обхода файловой системы,
что позволяет исследовать структуру директорий и файлов.

В общем, цель этого модуля - облегчить работу с файловой системой, предоставив
удобный и понятный интерфейс для взаимодействия с ней.
"""

from __future__ import annotations
from typing import Final, Iterator, Callable, cast
from abc import ABC, abstractmethod
import os
import sys
from fnmatch import fnmatch

from modules.contracts import contract, has_valid_dir_path
from modules.protocols import (
    Configs,
    SortTypeLiteral,
)
from modules.logger import get_logger
from modules.sort import sort_to

LOGGER: Final = get_logger(__name__)


class FileSystemElement(ABC):
    """Абстрактный класс описывающий элемент ФС производный от DirEntryProtocol.

    Свойства:
    - name: str
    - path: str
    - is_dir
    - is_file
    - is_symlink
    - level: int - уровень вложенности элемента (0 - корневой элемент).
    - is_hidden: bool - является ли элемент скрытым.
    - parent: DirectoryElement - родительский элемент.
    - is_immutable: bool - флаг, указывающий, что элемент не может быть изменен (нет прав на запись
       у родительской директории).
    - is_last_in_list: bool - флаг, указывающий, что элемент является последним в списке элементов.

    """

    def __init__(self, name: str, path: str, parent: DirectoryElement) -> None:
        """Инициализация

        Params:
        - name: str - имя элемента.
        - path: str - путь к элементу.
        - parent: DirectoryElement - родительский элемент.
        """
        # Элемент ФС
        self.__name: Final = name
        self.__path: Final = path
        self.__parent: Final = parent

        self._last_in_list = False

    @property
    def name(self) -> str:
        """Имя элемента"""
        return self.__name

    @property
    def path(self) -> str:
        """Путь к элементу"""
        return self.__path

    @property
    @abstractmethod
    def is_dir(self) -> bool:
        """Является ли элемент директорией"""
        raise NotImplementedError

    @property
    @abstractmethod
    def is_file(self) -> bool:
        """Является ли элемент файлом"""
        raise NotImplementedError

    @property
    def is_symlink(self) -> bool:
        """Является ли элемент символической ссылкой"""
        return os.path.islink(self.path)

    @property
    def level(self) -> int:
        """Уровень вложенности элемента"""
        return self.parent.level + 1

    @property
    def is_hidden(self) -> bool:
        """Является ли элемент скрытым"""
        return FileSystemElement.check_is_hidden(self.name)

    @property
    def parent(self) -> DirectoryElement:
        """Родительский элемент"""
        return self.__parent

    @property
    def is_immutable(self):
        """Флаг, указывающий, что элемент не может быть изменен (нет прав на запись у родительской директории)"""
        return not self.parent.is_writable

    @property
    def is_last_in_list(self):
        """Флаг, указывающий, что элемент является последним в списке элементов."""
        return self._last_in_list

    def __repr__(self):
        return f"{self.path}{os.path.sep if self.is_dir else ''}"

    @staticmethod
    def check_is_hidden(name: str) -> bool:
        """Проверяет, является ли элемент скрытым."""
        # @fixme: этот способ определения скрытых файлов платформозависимый
        return name.startswith(".") or name.endswith("~")


class FileElement(FileSystemElement):
    """Класс FileElement описывает файл."""

    def __init__(self, name: str, path: str, parent: DirectoryElement) -> None:
        super().__init__(name, path, parent)

        self.__name_without_ext: Final
        self.__extension: Final
        # @todo: корректно обрабатывать файлы с двойными расширениями. ( example.tar.gz )
        self.__name_without_ext, self.__extension = os.path.splitext(self.name)

    @property
    def is_dir(self) -> bool:
        """Является ли элемент директорией"""
        return False

    @property
    def is_file(self) -> bool:
        """Является ли элемент файлом"""
        return True

    @property
    def extension(self) -> str:
        """Расширение файла"""
        return self.__extension

    @property
    def name_without_ext(self) -> str:
        """Имя файла без расширения"""
        return self.__name_without_ext


class DirectoryElement(FileSystemElement):
    """Класс DirectoryElement описывает директорию."""

    def __init__(self, name: str, path: str, parent: DirectoryElement, config: Configs) -> None:
        """
        Инициализирует объект DirectoryElement.
        """
        super().__init__(name, path, parent)

        # Список директорий в директории. создается и заполняется в get_content
        self.__content_directories: Final[list[DirectoryElement]] = []
        # Список файлов в директории. создается и заполняется в get_content
        self.__content_files: Final[list[FileElement]] = []

        self._load_content(config)

    # @todo: Подозреваю, это можно распараллеливать.
    def _load_content(self, config: Configs) -> None:
        """Заполняет списки файлов и директорий self._content_directories и self._content_files содержимым
        директории.

        Будет обойдено дерево файловой системы начиная с текущей директории с учетом параметров обхода, и
        заполнены списки файлов и директорий объектами FileSystemElement.

        Состояние фс будет "заморожено" на момент обхода, т.е. изменения в файловой системе после вызова метода
        не будут учтены.

        Params:
        - config: Config - Конфигурация обхода директории.
            - depth: int - Рекурсивный обход поддиректорий. Будет пройдено дерево до указанной глубины.
                    - N<0 - все директории.
                    - 0 - только текущая директория.
                    - 1..N - текущая директория и N уровней поддиректорий.
            - subdirectories: bool - Учитывать поддиректории. Как минимум поддиректории корня будут содержатся
                                в content_directories, но будут пусты.
            - hidden: bool - Учитывать скрытые элементы. Если False, то скрытые элементы не будут включены в
                               content_directories и content_files.
            - sort: SortTypeLiteral - метод сортировки элементов. При любом значении, кроме "none" директории всегда
                                        сортируются по имени.
            - filters: list[str] - Список фильтров (globing) для файлов. Файлы, имена которых соответствуют хотя
                                     бы одному фильтру, будут включены в content_files.

        Замечания:

        Должен быть вызван в конструкторе объекта DirectoryElement перед обращением
        к self.content_directories и self.content_files.
        """

        # Получает содержимое директории.
        # Заполняет списки файлов (self._content_files) и директорий (self._content_directories).

        try:
            for entry_name in os.listdir(self.path):
                if self.level < 1 or (  # если текущий уровень меньше 1 (корень)
                    config["depth"] - self.level + 1
                ):  # или если задано в config обходить не все дерево

                    if not config["hidden"] and FileElement.check_is_hidden(entry_name):
                        continue  # если задано в configs пропускать скрытые элементы

                    entry_path: Final = os.path.join(self.path, entry_name)

                    if os.path.isdir(entry_path):  # если это директория
                        if config["subdirectories"]:
                            self.__content_directories.append(DirectoryElement(entry_name, entry_path, self, config))

                    else:  # если это файл
                        # применяет фильтры
                        if any(fnmatch(entry_name, pattern) for pattern in config["filters"]):
                            self.__content_files.append(FileElement(entry_name, entry_path, self))

        except PermissionError:
            print(f"Нет доступа к директории: {self.path}", file=sys.stderr)
        except OSError as e:
            print(f"Ошибка: {self.path}.", e, file=sys.stderr)

        if self.__content_files:
            # Сортирует файлы.
            self.__content_files.sort(key=sort_to(config["sort"]))
        if self.__content_directories:
            # Сортирует директории.
            if config["sort"] != "none":  # директории всегда сортируются по имени
                self.__content_directories.sort(key=sort_to("iname"))

        self._mark_last()  # последний файл в списке пометить как "последний"

    @property
    def is_dir(self) -> bool:
        """Является ли элемент директорией"""
        return True

    @property
    def is_file(self) -> bool:
        """Является ли элемент файлом"""
        return False

    @property
    def is_empty(self) -> bool:
        """Проверяет, что директория "пуста". Т.е. content_files и content_directories не содержат элементов."""
        return not self.content_files and not self.content_directories

    @property
    def is_writable(self) -> bool:
        """Проверяет, доступна ли директория для записи."""
        return os.access(self.path, os.W_OK)

    @property
    def content_directories(self) -> list[DirectoryElement]:
        """Список поддиректорий в директории."""
        return self.__content_directories

    @property
    def content_files(self) -> list[FileElement]:
        """Список файлов в директории."""
        return self.__content_files

    def print_content(self):
        """Печатает содержимое директории в виде дерева."""

        def func(element: FileElement | DirectoryElement) -> None:

            if element.is_file:
                marker = "└─" if element.is_last_in_list else "├─"
                print(" " * (element.level - 1) + marker + " " + element.name)

            if element.is_dir:
                print(" " * (element.level) + "* " + element.name)
                if cast(DirectoryElement, element).is_empty:
                    # печатать сообщение "пусто" для пустых папок
                    print(" " * (element.level) + "└─ < пусто >")

        func(self)
        self.apply_to_each(func)

    def apply_to_each(self, func: Callable[[FileElement | DirectoryElement], None]) -> None:
        """Применяет функцию к каждому элементу в дереве. Начиная обход от текущей директории.

        Функция func будет вызвана для каждого под-элемента, но не для самого элемента.
        Это значит что следующий код не напечатает имя корневой директории:
            ```
            root = RootDirectory("path/to/root", ...)
            root.apply_to_each(lambda element: print(element.name))
            ```
            возможный вывод:
            ```
            file1
            file2
            file3
            dir1
            dir2
            ```
            Имя корневой директории root не напечатано!

        Функция будет вызвана сначала для всех файлов в корне, потом для первой поддиректории и, затем,
        ко всем ее файлам и т.д. Потом для второй поддиректории и, затем, ко всем ее файлам и т.д. И т.д.


        Params:
        - func: (FileElement | DirectoryElement) -> None - функция, которая будет применена к
                   каждому элементу.

        """

        if self.is_empty:
            return

        for file in self.content_files:
            func(file)

        for directory in self.content_directories:
            func(directory)
            directory.apply_to_each(func)

    def __iter__(self) -> Iterator[FileElement | DirectoryElement | None]:
        """Возвращает итератор, который перебирает все элементы в дереве, начиная с текущей директории."""
        if self.is_empty:
            yield None
        for file in self.content_files:
            yield file
        for directory in self.content_directories:
            yield directory
            yield from directory.__iter__()

    def _mark_last(self):

        if self.content_files:
            self.content_files[-1]._last_in_list = True  # pylint: disable=protected-access
        if self.content_directories:
            self.content_directories[-1]._last_in_list = True  # pylint: disable=protected-access


class RootDirectoryElement(DirectoryElement):
    """Класс RootDirectory описывает корневую директорию."""

    @contract(has_valid_dir_path)
    def __init__(self, path: str, configs: Configs, /) -> None:
        """
        Инициализирует объект RootDirectoryElement.

        Params:
            - path: str - путь к директории. Путь должен существовать и быть директорией. Путь будет нормализован и
                            преобразован в абсолютный путь.
            - configs - Конфигурация обхода:
                - depth: int - глубина обхода директории. Если depth < 0, то будет обойдено все дерево.
                                Если depth == 0, то обход будет только в текущей директории.
                                Если depth > 0, то обход будет до указанной глубины.
                - subdirectories: bool - учитывать поддиректории.
                - hidden: bool - учитывать скрытые элементы.
                - sort: SortTypeLiteral - метод сортировки элементов. При любом значении, кроме "none" директории всегда
                                            сортируются по имени.
                - filters: list[str] - список фильтров (globing) для файлов.
        """
        if not os.path.isdir(path):
            raise FileNotFoundError(f"Директория не найдена: {path}")
        _path: Final = os.path.abspath(os.path.normpath(os.path.expanduser(path)))
        _name: Final = os.path.basename(_path)

        # инициализация базового класса
        super().__init__(_name, _path, self, configs)

    @property
    def level(self):
        return 0


if __name__ == "__main__":
    pass
