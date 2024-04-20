#!/usr/bin/env python3
"""
__file__ = "fs_elements.py"
Модуль `fs_elements` содержит реализацию классов для работы с элементами файловой системы.

Основные классы:

- `DirEntryProtocol` - интерфейс для работы с объектами, аналогичными `os.DirEntry`.
- `FileSystemElement` - абстрактный класс, описывающий элемент файловой системы, производный от `DirEntryProtocol`.
- `FileElement` и `DirectoryElement` - конкретные реализации для работы с файлами и директориями.
- `RootDirectoryElement` - класс, представляющий корневую директорию.

Эти классы позволяют получить информацию о файлах и директориях, а также обойти файловую систему
 и вывести ее содержимое в виде дерева.

Модуль `fs_elements` предназначен для представления и взаимодействия с элементами
файловой системы. Он содержит классы, моделирующие файлы и директории, и
предоставляет методы для получения информации о них, такие как имя, путь и тип.

Этот модуль также предоставляет функциональность для обхода файловой системы,
что позволяет исследовать структуру директорий и файлов.

В общем, цель этого модуля - облегчить работу с файловой системой, предоставив
удобный и понятный интерфейс для взаимодействия с ней.
"""

from __future__ import annotations
from typing import Final, Iterator, List, Optional, Union, Callable, cast
from abc import ABC
import os
import sys
from fnmatch import fnmatch

from modules.protocols import (
    DirEntryProtocol,
    FSElementProtocol,
    FileElementProtocol,
    DirectoryElementProtocol,
    Configs,
    SortTypeLiteral,
)
from modules.logger import get_logger
from modules.sort import sort_method

LOGGER: Final = get_logger(__name__)


class FileSystemElement(ABC, FSElementProtocol):
    """Абстрактный класс описывающий элемент ФС производный от `DirEntryProtocol`.

    Расширяет интерфейс `DirEntryProtocol`
    Переопределяет методы как свойства:
    - `is_dir`
    - `is_file`
    - `is_symlink`
    - `stat`
    Добавляя свойства:
    - `level: int` - уровень вложенности элемента (0 - корневой элемент).
    - `is_hidden: bool` - является ли элемент скрытым.
    - `parent: DirectoryElement` - родительский элемент.
    - `immutable: bool` - флаг, указывающий, что элемент не может быть изменен (нет прав на запись
       у родительской директории).
    - `is_last_in_list: bool` - флаг, указывающий, что элемент является последним в списке элементов.

    """

    def __init__(
        self,
        entry: DirEntryProtocol,
        parent: DirectoryElement,
    ) -> None:  # Инициализация
        # Элемент ФС
        self.__entry: Final = entry
        self.__parent: Final = parent

        self._last_in_list = False

    # region Методы реализующие протокол DirEntryProtocol

    @property
    def name(self) -> str:
        """Имя элемента"""
        return self.__entry.name

    @property
    def path(self) -> str:
        """Путь к элементу"""
        return self.__entry.path

    def inode(self) -> int:
        """Индексный дескриптор элемента"""
        return self.__entry.inode()

    def is_dir(self, *, follow_symlinks: bool = True) -> bool:
        """Является ли элемент директорией"""
        return self.__entry.is_dir(follow_symlinks=follow_symlinks)

    def is_file(self, *, follow_symlinks: bool = True) -> bool:
        """Является ли элемент файлом"""
        return self.__entry.is_file(follow_symlinks=follow_symlinks)

    def is_symlink(self) -> bool:
        """Является ли элемент символической ссылкой"""
        return self.__entry.is_symlink()

    def stat(self, *, follow_symlinks: bool = True) -> os.stat_result:
        """Возвращает информацию о файле (`os.stat()`)"""
        return self.__entry.stat(follow_symlinks=follow_symlinks)

    # endregion

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
    def immutable(self):
        """Флаг, указывающий, что элемент не может быть изменен (нет прав на запись у родительской директории)"""
        return not self.parent.is_writable

    @property
    def is_last_in_list(self):
        return self._last_in_list

    def __repr__(self):
        return f"{self.path}{os.path.sep if self.is_dir() else ''}"

    @staticmethod
    def check_is_hidden(name: str) -> bool:
        """Проверяет, является ли элемент скрытым."""
        # @fixme: этот способ определения скрытых файлов платформозависимый
        return name.startswith(".") or name.endswith("~")


class FileElement(FileSystemElement, FileElementProtocol):
    """Класс FileElement описывает файл."""

    def __init__(self, entry: DirEntryProtocol, parent: DirectoryElement) -> None:
        super().__init__(entry, parent)

        # @todo: корректно обрабатывать файлы с двойными расширениями. ( `example.tar.gz` )
        self.__name_without_ext, self.__extension = os.path.splitext(entry.name)

    @property
    def extension(self) -> str:
        """Расширение файла"""
        return self.__extension

    @property
    def name_without_ext(self) -> str:
        """Имя файла без расширения"""
        return self.__name_without_ext


class DirectoryElement(FileSystemElement, DirectoryElementProtocol):
    """Класс DirectoryElement описывает директорию."""

    def __init__(self, entry: DirEntryProtocol, parent: DirectoryElement, config: Configs) -> None:
        """
        Инициализирует объект DirectoryElement.
        """
        super().__init__(entry, parent)

        # Список директорий в директории. создается и заполняется в `get_content`
        self.__content_directories: Final[List[DirectoryElement]] = []
        # Список файлов в директории. создается и заполняется в `get_content`
        self.__content_files: Final[List[FileElement]] = []

        self._load_content(config)

    # @todo: Подозреваю, это можно распараллеливать.
    def _load_content(self, config: Configs) -> None:
        """Заполняет списки файлов и директорий `self._content_directories` и `self._content_files` содержимым
        директории.

        Будет обойдено дерево файловой системы начиная с текущей директории с учетом параметров обхода, и
        заполнены списки файлов и директорий объектами `FileSystemElement`.

        Состояние фс будет "заморожено" на момент обхода, т.е. изменения в файловой системе после вызова метода
        не будут учтены.

        Params:
        - `config: Config` - Конфигурация обхода директории.
            - `depth: int` - Рекурсивный обход поддиректорий. Будет пройдено дерево до указанной глубины.
                    - N<0 - все директории.
                    - 0 - только текущая директория.
                    - 1..N - текущая директория и N уровней поддиректорий.
            - `subdirectories: bool` - Учитывать поддиректории. Как минимум поддиректории корня будут содержатся
                                в `content_directories`, но будут пусты.
            - `hidden: bool` - Учитывать скрытые элементы. Если `False`, то скрытые элементы не будут включены в
                               `content_directories` и `content_files`.
            - `sort: str` -
            - `filters: List[str]` -
            # @todo:
            - `follow_symlinks: bool` - Следовать ли по символическим ссылкам.

        Замечания:

        Должен быть вызван в конструкторе объекта `DirectoryElement` перед обращением
        к `self.content_directories` и `self.content_files`.
        """

        # Получает содержимое директории.
        # Заполняет списки файлов (self._content_files) и директорий (self._content_directories).

        try:
            with os.scandir(self.path) as entries:
                for _entry in entries:
                    if (
                        config["depth"] - self.level + 1
                    ) or self.level < 1:  # если задано в config обходить не все дерево
                        # содержимое корня обрабатывается всегда

                        if not config["hidden"] and FileElement.check_is_hidden(_entry.name):
                            continue  # если задано в configs пропускать скрытые элементы

                        if _entry.is_dir():
                            if config["subdirectories"]:  # если задано в config обрабатывать поддиректории
                                self.__content_directories.append(DirectoryElement(_entry, self, config))

                        else:  # _entry.is_file():
                            if any(fnmatch(_entry.name, pattern) for pattern in config["filters"]):
                                self.__content_files.append(FileElement(_entry, self))

        except PermissionError:
            print(f"Нет доступа к директории: {self.path}", file=sys.stderr)
        except OSError as e:
            print(f"Ошибка: {self.path}.", e, file=sys.stderr)

        if self.__content_files:
            # Сортировка файлов.
            self.__content_files.sort(key=sort_method(config["sort"]))
        if self.__content_directories:
            # Сортировка директорий.
            if config["sort"] != "none":  # директории всегда сортируются по имени
                self.__content_directories.sort(key=sort_method("iname"))

        self._mark_last()  # последний файл в списке пометить как "последний"

    @property
    def is_empty(self) -> bool:
        """Проверяет, что директория "пуста". Т.е. `content_files` и `content_directories` не содержат элементов."""
        return not self.content_files and not self.content_directories

    @property
    def is_writable(self) -> bool:
        return os.access(self.path, os.W_OK)

    @property
    def content_directories(self) -> List[DirectoryElement]:
        """Список поддиректорий в директории."""
        return self.__content_directories

    @property
    def content_files(self) -> List[FileElement]:
        """Список файлов в директории."""
        return self.__content_files

    def print_content(self):
        """Печатает содержимое директории в виде дерева."""

        def func(element: Union[FileElement, DirectoryElement]) -> None:

            if element.is_file():
                marker = "└─" if element.is_last_in_list else "├─"
                print(" " * (element.level - 1) + marker + " " + element.name)

            if element.is_dir():
                print(" " * (element.level) + "* " + element.name)
                if cast(DirectoryElement, element).is_empty:
                    # печатать сообщение "пусто" для пустых папок
                    print(" " * (element.level) + "└─ < пусто >")

        func(self)
        self.apply_to_each(func)

    def apply_to_each(self, func: Callable[[Union[FileElement, DirectoryElement]], None]) -> None:
        """Применяет функцию к каждому элементу в дереве. Начиная обход от текущей директории.

        Функция `func` будет вызвана для каждого под-элемента, но не для самого элемента.
        Это значит что следующий код не напечатает имя корневой директории:

            ```python
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
            Имя корневой директории `root` не напечатано!

        Функция будет вызвана сначала для всех файлов в корне, потом для первой поддиректории и, затем,
        ко всем ее файлам и т.д. Потом для второй поддиректории и, затем, ко всем ее файлам и т.д. И т.д.


        Params:
        - `func: Callable[[Union[FileElement, DirectoryElement]], None]` - функция, которая будет применена к
                   каждому элементу.

        """

        if self.is_empty:
            return

        for file in self.content_files:
            func(file)

        for directory in self.content_directories:
            func(directory)
            directory.apply_to_each(func)

    def __iter__(self) -> Iterator[Optional[Union[FileElement, DirectoryElement]]]:
        """Возвращает итератор, который перебирает все элементы в дереве, начиная с текущей директории."""
        if self.is_empty:
            yield None
        for file in self.content_files:
            yield file
        for directory in self.content_directories:
            yield directory
            yield from directory.__iter__()

    def _mark_last(self):
        # pylint: disable=W0212
        if self.content_files:
            self.content_files[-1]._last_in_list = True
        if self.content_directories:
            self.content_directories[-1]._last_in_list = True
        # pylint: enable=W0212


class RootDirectoryElement(DirectoryElement, DirectoryElementProtocol):
    """Класс RootDirectory описывает корневую директорию."""

    def __init__(
        self,
        path: str,
        depth: int,
        subdirectories: bool,
        hidden: bool,
        sort: SortTypeLiteral,
        filters: List[str],
    ) -> None:
        """
        Инициализирует объект DirectoryElement.
        """

        class DirEntry(DirEntryProtocol):
            """Вспомогательный класс, реализация протокола DirEntryProtocol"""

            def __init__(self, path: str):
                self.__path: Final[str] = path

            @property
            def name(self) -> str:
                return os.path.basename(self.__path)

            @property
            def path(self) -> str:
                return self.__path

            def inode(self) -> int:
                return self.stat().st_ino

            def is_dir(self, *, follow_symlinks: bool = True) -> bool:  # @todo
                return os.path.isdir(self.__path)

            def is_file(self, *, follow_symlinks: bool = True) -> bool:  # @todo
                return os.path.isfile(self.path)

            def is_symlink(self) -> bool:
                return os.path.islink(self.__path)

            def stat(self, *, follow_symlinks: bool = True) -> os.stat_result:  # @todo
                return os.stat(self.__path, follow_symlinks=follow_symlinks)

        configs: Final[Configs] = {
            "depth": depth,
            "subdirectories": subdirectories,
            "hidden": hidden,
            "sort": sort,
            "filters": filters,
        }

        # инициализация базового класса
        super().__init__(DirEntry(os.path.abspath(os.path.normpath(os.path.expanduser(path)))), self, configs)

    @property
    def level(self):
        return 0


if __name__ == "__main__":
    pass
