#!/usr/bin/env python3
""""""

# pylint: disable=C0301,C0116

from __future__ import annotations
import os
from typing import Callable, Iterator, List, Literal, Optional, Protocol, TypedDict, Union


class DirEntryProtocol(Protocol):
    """
    Интерфейс для работы с объектами `os.DirEntry`

    Свойства:
    - `name: str`
    - `path: str`

    Методы:
    - `inode: int`
    - `is_dir(follow_symlinks: bool = True) -> bool`
    - `is_file(follow_symlinks: bool = True) -> bool`
    - `is_symlink() -> bool`
    - `stat(follow_symlinks: bool = True) -> os.stat_result`
    """

    @property
    def name(self) -> str: ...
    @property
    def path(self) -> str: ...
    def inode(self) -> int: ...
    def is_dir(self, *, follow_symlinks: bool = True) -> bool: ...
    def is_file(self, *, follow_symlinks: bool = True) -> bool: ...
    def is_symlink(self) -> bool: ...
    def stat(self, *, follow_symlinks: bool = True) -> os.stat_result: ...


class FSElementProtocol(DirEntryProtocol, Protocol):
    """

    Расширяет интерфейс `DirEntryProtocol`

    Добавляя свойства:
    - `level: int` - уровень вложенности элемента (0 - корневой элемент).
    - `is_hidden: bool` - является ли элемент скрытым.
    - `parent: DirectoryElementProtocol` - родительский элемент.
    - `immutable: bool` - флаг, указывающий, что элемент не может быть изменен (нет прав на запись у родительской директории).
    - `is_last_in_list: bool` - флаг, указывающий, что элемент является последним в списке элементов.
    """

    @property
    def level(self) -> int: ...

    @property
    def is_hidden(self) -> bool: ...

    @property
    def parent(self) -> DirectoryElementProtocol: ...

    @property
    def immutable(self) -> bool: ...

    @property
    def is_last_in_list(self) -> bool: ...

    # @property
    # def frmt_name(self) -> str: ...


class FileElementProtocol(FSElementProtocol, Protocol):
    """

    Класс FileElementProtocol описывает файл.

    Свойства:
    - `extension: str` - расширение файла.
    - `name_without_ext: str` - имя файла без расширения.
    """

    @property
    def extension(self) -> str: ...

    @property
    def name_without_ext(self) -> str: ...


class DirectoryElementProtocol(FSElementProtocol, Protocol):
    """

    Класс DirectoryElementProtocol описывает директорию.

    Свойства:
    - `is_empty: bool` - является ли директория "пустой".
    - `content_directories: List[DirectoryElementProtocol]` - список вложенных директорий.
    - `content_files: List[FileElementProtocol]` - список вложенных файлов.
    - `is_writable: bool` - доступна ли директория для записи.

    Методы:
    - `apply_to_each(func: Callable[[Union[FileElementProtocol, DirectoryElementProtocol]], None]) -> None` - применяет функцию к каждому под-элементу.

    Итератор:
    - `__iter__` - итератор, возвращающий под-элементы директории.
    """

    @property
    def is_empty(self) -> bool: ...

    @property
    def is_writable(self) -> bool: ...

    @property
    def content_directories(self) -> List[DirectoryElementProtocol]: ...

    @property
    def content_files(self) -> List[FileElementProtocol]: ...

    def apply_to_each(self, func: Callable[[Union[FileElementProtocol, DirectoryElementProtocol]], None]) -> None: ...

    def __iter__(self) -> Iterator[Optional[Union[FileElementProtocol, DirectoryElementProtocol]]]: ...


class Configs(TypedDict):

    depth: int
    subdirectories: bool
    hidden: bool
    # sort: Literal[
    #     "name",
    #     "type",
    #     "mime",
    # ]


if __name__ == "__main__":
    pass
