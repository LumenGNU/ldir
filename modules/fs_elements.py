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
from abc import ABC, abstractmethod
import os
import sys
from typing import List, Optional, Protocol, Union, runtime_checkable, Callable, cast

from .logger import get_logger

logger = get_logger(__name__)


@runtime_checkable  # @todo: а этот декоратор и правда нужен?
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
        self._entry = entry
        self.__parent: Optional[DirectoryElement] = None

        self._level = level
        # @fixme: этот способ определения скрытых файлов платформозависимый
        self._is_hidden = self._entry.name.startswith(".")

    # region Методы реализующие протокол DirEntryProtocol

    @property
    def name(self) -> str:
        """Имя элемента"""
        return self._entry.name

    @property
    def path(self) -> str:
        """Путь к элементу"""
        return self._entry.path

    @property
    def inode(self) -> int:
        """Индексный дескриптор элемента"""
        return self._entry.inode()

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
        return self._entry.is_symlink()

    @property
    def stat(self) -> os.stat_result:
        """Возвращает информацию о файле (`os.stat()`)"""
        return self._entry.stat()

    # endregion

    @property
    def level(self) -> int:
        """Уровень вложенности элемента"""
        return self._level

    @property
    def is_hidden(self) -> bool:
        """Является ли элемент скрытым"""
        return self._is_hidden

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


class Config:
    """Класс для хранения конфигурации обхода директории.

    Конфигурация  *замораживается после первого вызова* метода  `set_config` (обычно в `RootDirectory`).
    Повторные вызовы метода `set_config`, для этого же объекта, с другими параметрами игнорируются.
    """

    def __init__(self) -> None:
        self.__recursive: bool = False
        self.__subdirectories: bool = True
        self.__hidden: bool = False
        self._config_is_set: bool = False

    @property
    def recursive(self):
        """Возвращает значение флага recursive."""
        return self.__recursive

    @property
    def subdirectories(self):
        """Возвращает значение флага subdirectories."""
        return self.__subdirectories

    @property
    def hidden(self):
        """Возвращает значение флага hidden."""
        return self.__hidden

    def set_config(
        self,
        recursive: Optional[bool] = None,
        subdirectories: Optional[bool] = None,
        hidden: Optional[bool] = None,
    ) -> Config:
        """Устанавливает конфигурацию для обхода директории.

        Если любой из параметров не установлен (None), то конфигурация не устанавливается.
        """
        if not self._config_is_set:
            if all(x is not None for x in (recursive, subdirectories, hidden)):
                # если все параметры имеют значения
                self.__recursive = cast(bool, recursive)
                self.__subdirectories = True if self.__recursive else cast(bool, subdirectories)
                self.__hidden = cast(bool, hidden)
                self._config_is_set = True
            else:
                logger.debug("Конфигурация НЕ установлена!")  # @for_debug
        else:
            logger.debug("Конфигурация УЖЕ установлена!")  # @for_debug

        return self

    def __repr__(self) -> str:
        return f"Config: (recursive={self.recursive}, subdirectories={self.subdirectories}, hidden={self.hidden})"


class DirectoryElement(FileSystemElement):
    """Класс DirectoryElement описывает директорию."""

    def __init__(self, entry: Union[DirEntryProtocol, os.DirEntry], level: int, config: Config) -> None:
        """
        Инициализирует объект DirectoryElement.
        """
        super().__init__(entry, level)

        # Список директорий в директории. создается и заполняется в `get_content`
        self._content_directories: Optional[List[DirectoryElement]] = None
        # Список файлов в директории. создается и заполняется в `get_content`
        self._content_files: Optional[List[FileElement]] = None
        self.__config = config

        self._load_content(self.__config)

    # @todo: Подозреваю, это можно распараллеливать.
    # @todo: Фильтрация!
    # @todo: `sort`: `Callable[[FileSystemElement], Any]` - Функция сортировки элементов.
    # @todo: `filter`: `Callable[[FileSystemElement], bool]` - Функция фильтрации элементов. Если функция вернет `True`,

    def _load_content(self, config: Config) -> None:
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

        if self._content_directories is None or self._content_files is None:

            self._content_directories = []
            self._content_files = []
            # Получает содержимое директории.
            # Заполняет списки файлов (self._content_files) и директорий (self._content_directories).
            try:
                with os.scandir(self.path) as entries:
                    for _entry in entries:
                        if config.recursive or self.level < 1:
                            if _entry.is_dir():
                                if config.subdirectories:
                                    element_directory = DirectoryElement(_entry, self.level + 1, config)
                                    if config.hidden or not element_directory.is_hidden:
                                        element_directory.parent = self
                                        self._content_directories.append(element_directory)
                                    else:
                                        del element_directory
                            else:  # _entry.is_file():
                                element_file = FileElement(_entry, self.level + 1)
                                if config.hidden or not element_file.is_hidden:
                                    element_file.parent = self
                                    self._content_files.append(element_file)
                                else:
                                    del element_file
            except PermissionError:
                print(f"Нет доступа к директории: {self.path}", file=sys.stderr)

            # @todo: Сортировка.

    @property
    def is_file(self):
        return False

    @property
    def is_dir(self):
        return True

    @property
    def is_empty(self) -> bool:
        """Проверяет, что директория "пуста". Т.е. `content_files` и `content_directories` пусты."""
        return not self.content_files and not self.content_directories

    @property
    def content_directories(self) -> List[DirectoryElement]:
        """Список поддиректорий в директории."""
        return cast(List[DirectoryElement], self._content_directories)

    @property
    def content_files(self) -> List[FileElement]:
        """Список файлов в директории."""
        return cast(List[FileElement], self._content_files)

    def print_content(self):
        """Печатает содержимое директории в виде дерева."""

        def func(element: Optional[FileSystemElement], is_last: bool, level: int) -> None:
            if element is None:
                # печатать сообщение "пусто" для пустых папок
                print(" " * (level) + "└─ < пусто >")
                return

            if element.is_file:
                marker = "└─" if is_last else "├─"
                print(" " * (element.level - 1) + marker + " " + element.name)

            if element.is_dir:
                print(" " * (element.level) + "* " + element.name)

        func(self, self.is_empty, 0)
        self.apply_to_each(func)

    def apply_to_each(self, func: Callable[[Optional[FileSystemElement], bool, int], None]) -> None:
        """Применяет функцию к каждому элементу в дереве.

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
            func(None, True, self.level)
            return

        len_ = len(self.content_files)
        for i, file in enumerate(self.content_files, start=1):
            func(cast(FileSystemElement, file), len_ - i < 1, self.level + 1)

        len_ = len(self.content_directories)
        for i, directory in enumerate(self.content_directories, start=1):
            func(cast(FileSystemElement, directory), len_ - i < 1, self.level + 1)
            cast(DirectoryElement, directory).apply_to_each(func)


class RootDirectoryElement(DirectoryElement):
    """Класс RootDirectory описывает корневую директорию."""

    def __init__(self, path: str, recursive: bool, subdirectories: bool, hidden: bool) -> None:
        """
        Инициализирует объект DirectoryElement.
        """

        class DirEntry(DirEntryProtocol):
            """Вспомогательный класс, реализация протокола DirEntryProtocol"""

            def __init__(self, path: str):
                self._path = path
                self._name = os.path.basename(path)
                self._is_dir = os.path.isdir(path)
                self._is_file = os.path.isfile(path)
                self._is_symlink = os.path.islink(path)
                self._stat = os.stat(path)

            @property
            def name(self) -> str:
                return self._name

            @property
            def path(self) -> str:
                return self._path

            def inode(self) -> int:
                return self._stat.st_ino

            def is_dir(self, *, follow_symlinks: bool = True) -> bool:
                return self._is_dir

            def is_file(self, *, follow_symlinks: bool = True) -> bool:
                return self._is_file

            def is_symlink(self) -> bool:
                return self._is_symlink

            def stat(self, *, follow_symlinks: bool = True) -> os.stat_result:
                return self._stat

        config = Config().set_config(recursive, subdirectories, hidden)

        # инициализация базового класса
        super().__init__(DirEntry(os.path.abspath(os.path.normpath(path))), level=0, config=config)


if __name__ == "__main__":
    pass
