#!/usr/bin/env python3
"""Реализация класса Entity"""

from typing import Tuple, Optional
import stat
from pathlib import Path
import tempita


class MemberString(str):

    __value: int

    def __new__(cls, text: str, value: Optional[int] = None):
        # Создание экземпляра str
        obj = str.__new__(cls, text)
        # Инициализация дополнительных атрибутов
        if value is not None:
            cls.__value = max(value, cls.__value)
        else:
            cls.__value = max(len(text), cls.__value)

        return obj

    @property
    def max_length(self) -> int:
        return MemberString.__value


class Entity:

    _NAME_MAX_LENGTH = 0
    _INO_MAX_LENGTH = 0

    def __init__(self, path: str):
        self._user_path = path
        self._path = Path(self._user_path).absolute()
        Entity._INO_MAX_LENGTH = max(Entity._INO_MAX_LENGTH, len(str(self._path.stat().st_ino)) + 2)
        Entity._NAME_MAX_LENGTH = max(Entity._NAME_MAX_LENGTH, len(self._path.name) + 5)

    @property
    def name(self) -> Tuple[str, int]:
        """Имя"""
        return self._path.name, Entity._NAME_MAX_LENGTH

    @property
    def path(self) -> str:
        """Абсолютный путь"""
        return str(self._path)

    @property
    def is_file(self) -> bool:
        """True -- если файл"""
        return self._path.is_file()

    @property
    def is_dir(self) -> bool:
        """True -- если директория"""
        return self._path.is_dir()

    @property
    def innode(self) -> Tuple[int, int]:
        """Inod-номер"""
        return self._path.stat().st_ino, Entity._INO_MAX_LENGTH

    @property
    def mode_oct(self) -> str:
        """Строка с правами доступа в виде последовательности восьмиричных цифр"""
        return oct(self._path.stat().st_mode).split("o")[-1]

    @property
    def mode_str(self) -> str:
        """Строка с правами доступа в человеко-читаемом виде '-rwxrwxrwx'"""
        return stat.filemode(self._path.stat().st_mode)

    @staticmethod
    def _format(text, margin=0, esym="", just="ljust") -> str:
        return getattr(f"{text}{esym}", just)(margin) + " "

    def to_string_item(self, *args, level: int = 0) -> str:

        #     return (
        #         self._format(*self.innode, just="rjust", esym=":")
        #         + " " * level * 2
        #         + self._format(
        #             f'["{self.name[0]}"]' if self.is_dir else f'\t"{self.name[0]}"',
        #             margin=self.name[1],
        #             just="ljust",
        #         )
        #     )
        tmpl = tempita.Template("""{{ino}}: {{name}}""")
        return tmpl.substitute(
            ino=self.innode[0],
            name=f'["{self.name[0]}"]' if self.is_dir else f'\t"{self.name[0]}"',
        )


if __name__ == "__main__":
    e0 = Entity("./test/")
    e1 = Entity("./test/1")
    e2 = Entity("./test/2")
    e3 = Entity("./test/3")
    print(e0.to_string_item())
    print(e1.to_string_item())
    print(e2.to_string_item())
    print(e3.to_string_item("mode_str", "path", level=5))
