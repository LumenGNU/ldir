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
from typing import Generator, Iterator, List, Optional, Protocol, Union, Callable, cast, Dict, Any
from abc import ABC, abstractmethod
import os
import sys

from .logger import get_logger

logger = get_logger(__name__)


class DirEntryProtocol(Protocol):
    """Интерфейс для работы с объектами os.DirEntry
    методы:
    - name: str
    - path: str
    - inode: int
    - is_dir(follow_symlinks: bool = True) -> bool
    - is_file(follow_symlinks: bool = True) -> bool
    - is_symlink() -> bool
    - stat(follow_symlinks: bool = True) -> os.stat_result
    """

    # pylint: disable=C0116

    @property
    def name(self) -> str: ...
    @property
    def path(self) -> str: ...
    def inode(self) -> int: ...
    def is_dir(self, *, follow_symlinks: bool = True) -> bool: ...
    def is_file(self, *, follow_symlinks: bool = True) -> bool: ...
    def is_symlink(self) -> bool: ...
    def stat(self, *, follow_symlinks: bool = True) -> os.stat_result: ...

    # pylint: enable=C0116


class FileSystemElement(ABC):
    """Абстрактный класс описывающий элемент ФС производный от `DirEntryProtocol`.

    Расширяет интерфейс `DirEntryProtocol`
    Переопределяет методы как свойства:
    - `is_dir`
    - `is_file`
    - `is_symlink`
    - `stat`
    Добавляя свойства:
    - `level`: `int` - уровень вложенности элемента (0 - корневой элемент).
    - `is_hidden`: `bool` - является ли элемент скрытым.

    """

    def __init__(self, entry: Union[os.DirEntry, DirEntryProtocol], level: int) -> None:  # Инициализация
        # Элемент ФС
        self.__entry = entry
        self.__parent: Optional[DirectoryElement] = None

        self.__level = level
        # @fixme: этот способ определения скрытых файлов платформозависимый
        self.__is_hidden = self.__entry.name.startswith(".")

        self._last_in_dir = False

    # region Методы реализующие протокол DirEntryProtocol

    @property
    def name(self) -> str:
        """Имя элемента"""
        return self.__entry.name

    @property
    def path(self) -> str:
        """Путь к элементу"""
        return self.__entry.path

    @property
    def inode(self) -> int:
        """Индексный дескриптор элемента"""
        return self.__entry.inode()

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
        return self.__entry.is_symlink()

    @property
    def stat(self) -> os.stat_result:
        """Возвращает информацию о файле (`os.stat()`)"""
        return self.__entry.stat()

    # endregion

    @property
    def level(self) -> int:
        """Уровень вложенности элемента"""
        return self.__level

    @property
    def is_hidden(self) -> bool:
        """Является ли элемент скрытым"""
        return self.__is_hidden

    @property
    def parent(self) -> Optional[DirectoryElement]:
        """Родительский элемент"""
        return self.__parent

    @parent.setter
    def parent(self, parent: DirectoryElement) -> None:
        """Устанавливает родительский элемент"""
        if self.__parent is None:
            self.__parent = parent
        else:
            logger.debug("Родительский элемент уже установлен!")  # @for_debug

    @property
    def is_last_in_dir(self):
        return self._last_in_dir

    def __repr__(self):
        return f"{self.path}{'/' if self.is_dir else ''}"


class FileElement(FileSystemElement):
    """Класс FileElement описывает файл."""

    @property
    def is_dir(self) -> bool:
        """Является ли элемент директорией"""
        return False

    @property
    def is_file(self) -> bool:
        """Является ли элемент файлом"""
        return True


class DirectoryElement(FileSystemElement):
    """Класс DirectoryElement описывает директорию."""

    def __init__(self, entry: Union[DirEntryProtocol, os.DirEntry], level: int, **config: Dict[str, Any]) -> None:
        """
        Инициализирует объект DirectoryElement.
        """
        super().__init__(entry, level)

        # Список директорий в директории. создается и заполняется в `get_content`
        self.__content_directories: Optional[List[DirectoryElement]] = None
        # Список файлов в директории. создается и заполняется в `get_content`
        self.__content_files: Optional[List[FileElement]] = None

        self._load_content(**config)

    # @todo: Подозреваю, это можно распараллеливать.
    # @todo: Фильтрация!
    # @todo: `sort`: `Callable[[FileSystemElement], Any]` - Функция сортировки элементов.
    # @todo: `filter`: `Callable[[FileSystemElement], bool]` - Функция фильтрации элементов.

    def _load_content(self, **config: Dict[str, Any]) -> None:
        """Заполняет списки файлов и директорий `self._content_directories` и `self._content_files` содержимым
        директории.

        Будет обойдено дерево файловой системы начиная с текущей директории с учетом параметров конфигурации, и
        заполнены списки файлов и директорий объектами `FileSystemElement`.

        Состояние фс будет "заморожено" на момент обхода, т.е. изменения в файловой системе после вызова метода
        не будут учтены.

        Params:
        - `config`: `Config` - Конфигурация обхода директории.
            - `recursive`: `bool` - Рекурсивный обход поддиректорий. Будет пройдено все дерево.
            - `subdirectories`: `bool` - Учитывать поддиректории. Как минимум поддиректории корня будут содержатся
               в `content_directories`, но будут пусты.
            - `hidden`: `bool` - Учитывать скрытые элементы. Если `False`, то скрытые элементы не будут включены в
            `content_directories` и `content_files`.
            # @todo:
            - `follow_symlinks`: `bool` - Следовать ли по символическим ссылкам.

        Замечания:

        Должен быть вызван в конструкторе объекта `DirectoryElement` перед обращением
        к `self.content_directories` и `self.content_files`.
        """

        if self.__content_directories is None or self.__content_files is None:

            self.__content_directories = []
            self.__content_files = []
            # Получает содержимое директории.
            # Заполняет списки файлов (self._content_files) и директорий (self._content_directories).
            try:
                with os.scandir(self.path) as entries:
                    for _entry in entries:
                        if config["recursive"] or self.level < 1:  # если задано в config обходить все дерево
                            # содержимое корня обрабатывается всегда
                            if _entry.is_dir():
                                if config["subdirectories"]:  # если задано в config обрабатывать поддиректории
                                    element_directory = DirectoryElement(_entry, self.level + 1, **config)
                                    if (
                                        config["hidden"] or not element_directory.is_hidden
                                    ):  # если задано в config пропускать скрытые
                                        element_directory.parent = self
                                        self.__content_directories.append(element_directory)
                                    else:
                                        del element_directory
                            else:  # _entry.is_file():
                                element_file = FileElement(_entry, self.level + 1)
                                if (
                                    config["hidden"] or not element_file.is_hidden
                                ):  # если задано в config пропускать скрытые
                                    element_file.parent = self
                                    self.__content_files.append(element_file)
                                else:
                                    del element_file
            except PermissionError:
                print(f"Нет доступа к директории: {self.path}", file=sys.stderr)

            if self.__content_files:
                # @todo: Сортировка файлов.
                self.__content_files[-1]._last_in_dir = True  # последний файл в списке пометить как "последний"

            # @todo: Сортировка директорий. if self.__content_directories:

    @property
    def is_file(self):
        return False

    @property
    def is_dir(self):
        return True

    @property
    def is_empty(self) -> bool:
        """Проверяет, что директория "пуста". Т.е. `content_files` и `content_directories` не содержат элементов."""
        return not self.content_files and not self.content_directories

    @property
    def content_directories(self) -> List[DirectoryElement]:
        """Список поддиректорий в директории."""
        return cast(List[DirectoryElement], self.__content_directories)

    @property
    def content_files(self) -> List[FileElement]:
        """Список файлов в директории."""
        return cast(List[FileElement], self.__content_files)

    def print_content(self):
        """Печатает содержимое директории в виде дерева."""

        def func(element: Union[FileElement, DirectoryElement]) -> None:

            if element.is_file:
                marker = "└─" if element.is_last_in_dir else "├─"
                print(" " * (element.level - 1) + marker + " " + element.name)

            if element.is_dir:
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
            root.apply_to_each(lambda element, _, _: print(element.name))
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
        - `func`: `Callable[[Optional[FileSystemElement], bool], None]` - функция, которая будет применена к
                   каждому элементу.

        Функция `func` должна принимать три аргумента:
            - `element`: `Optional[FileSystemElement]` - элемент. None для "пустых" директорий.
            - `is_last`: `bool` - флаг, указывающий, является ли элемент последним в его родительском списке.
            - `level`: `int` - уровень вложенности элемента.
        """

        if self.is_empty:
            return

        for file in self.content_files:
            func(cast(FileElement, file))

        for directory in self.content_directories:
            func(cast(DirectoryElement, directory))
            cast(DirectoryElement, directory).apply_to_each(func)

    def __iter__(self) -> Iterator[Optional[Union[FileElement, DirectoryElement]]]:
        """Возвращает итератор, который перебирает все элементы в дереве, начиная с текущей директории."""
        if self.is_empty:
            yield None
        for file in self.content_files:
            yield file
        for directory in self.content_directories:
            yield directory
            yield from directory.__iter__()

    # def __iterate_all_elements(self) -> Generator[Optional[Union[FileElement, DirectoryElement]], None, None]:
    #     """Генератор для перебора дерева элементов."""
    #     if self.is_empty:
    #         yield None
    #     for file in self.content_files:
    #         yield file
    #     for directory in self.content_directories:
    #         yield directory
    #         yield from directory.__iterate_all_elements()


class RootDirectoryElement(DirectoryElement):
    """Класс RootDirectory описывает корневую директорию."""

    def __init__(self, path: str, recursive: bool, subdirectories: bool, hidden: bool) -> None:
        """
        Инициализирует объект DirectoryElement.
        """

        class DirEntry(DirEntryProtocol):
            """Вспомогательный класс, реализация протокола DirEntryProtocol"""

            def __init__(self, path: str):
                self.__path = path
                self.__name = os.path.basename(path)
                self.__is_dir = os.path.isdir(path)
                self.__is_file = os.path.isfile(path)
                self.__is_symlink = os.path.islink(path)
                self.__stat = os.stat(path)

            @property
            def name(self) -> str:
                return self.__name

            @property
            def path(self) -> str:
                return self.__path

            def inode(self) -> int:
                return self.__stat.st_ino

            def is_dir(self, *, follow_symlinks: bool = True) -> bool:
                return self.__is_dir

            def is_file(self, *, follow_symlinks: bool = True) -> bool:
                return self.__is_file

            def is_symlink(self) -> bool:
                return self.__is_symlink

            def stat(self, *, follow_symlinks: bool = True) -> os.stat_result:
                return self.__stat

        config: Dict[str, Any] = {
            "recursive": recursive,
            "subdirectories": True if recursive else subdirectories,
            "hidden": hidden,
        }

        # инициализация базового класса
        super().__init__(DirEntry(os.path.abspath(os.path.normpath(path))), level=0, **config)


if __name__ == "__main__":
    pass
