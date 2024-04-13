#!/usr/bin/env python3
""" 
Класс-приложение ldir
"""

import os
import shutil
import argparse


class App:
    """Singleton class to store application parameters"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        self._cl_params = self.parse_args()
        self._cl_params.editor = self.choose_editor()

    @property
    def cl_params(self) -> argparse.Namespace:
        """
        Возвращает объект с аргументами командной строки.

        Returns:
            `argparse.Namespace`: Объект с аргументами:

            - `directory_path`: `str` - Путь к директории для обработки. По умолчанию текущая директория.
            - `editor`: `str` - Программа, которая будет вызвана в качестве редактора.
            - `editor-args`: `str` - Аргументы запуска для редактора.
            - `recursive`: `bool` - Рекурсивно обрабатывать подкаталоги.
            - `directory`: `bool` - Обрабатывать поддиректории.
            - `hidden`: `bool` - Обрабатывать скрытые элементы.
        """
        return self._cl_params

    def parse_args(self) -> argparse.Namespace:
        """
        Парсит аргументы командной строки.

        Returns:
            argparse.Namespace: Объект с аргументами командной строки.
        """
        # Создаем парсер
        parser = argparse.ArgumentParser(
            description="ldir - утилита для удобной работы с большим количеством файлов и каталогов.",
            add_help=False,
        )

        # region group_Общие
        group_0 = parser.add_argument_group("Общие")
        group_0.add_argument(
            "-h",
            "--help",
            action="help",
            default=argparse.SUPPRESS,
            help="Показать справку и выйти.",
        )
        # endregion

        # region позиционный аргумент
        # Добавляем позиционный аргумент
        parser.add_argument_group("Позиционный параметр").add_argument(
            "directory_path",
            type=str,
            nargs="?",
            default=".",
            help="Путь к директории для обработки. По умолчанию текущая директория.",
        )
        # endregion

        # region group_editor
        # Добавляем аргументы
        group_editor = parser.add_argument_group("Редактор")
        group_editor.add_argument(
            "-e",
            "--editor",
            type=str,
            required=False,
            default="",
            help="Программа которая будет вызвана в качестве редактора.",
        )
        group_editor.add_argument(
            "-g",
            "--editor-args",
            type=str,
            required=False,
            default="",
            help="Аргументы запуска для редактора.",
        )
        # endregion

        # region group_catalog
        group_catalog = parser.add_argument_group("Каталог")
        group_catalog.add_argument(
            "-r",
            "--recursive",
            type=int,
            default=-1,
            action="store_true",
            required=False,
            help="Флаг, рекурсивно обрабатывать подкаталоги (False).",
        )
        group_catalog.add_argument(
            "-d",
            "--directory",
            action="store_true",
            required=False,
            help="Флаг, обрабатывать поддиректории (False).",
        )
        group_catalog.add_argument(
            "-a",
            "--hidden",
            action="store_true",
            required=False,
            help="Флаг, обрабатывать скрытые элементы (False).",
        )

        # endregion

        # Парсим аргументы
        _cl_params = parser.parse_args()

        # проверки

        # путь self._cl_params.directory_path -- должен существовать и быть директорией
        if not os.path.isdir(_cl_params.directory_path):
            raise ValueError(f"Указанный путь не существует или не является директорией! {_cl_params.directory_path}")

        # команда в self._cl_params.editor -- должна быть доступна в $PATH или по путь и
        # иметь разрешение на выполнение
        # команда в self._cl_params.editor -- не может быть пустой строкой
        if _cl_params.editor and _cl_params.editor.strip():
            if not shutil.which(_cl_params.editor):
                raise ValueError(f"Указанная команда не найдена или нет прав на запуск: {_cl_params.editor}")

        return _cl_params

    def choose_editor(self) -> str:
        """Выбор редактора."""

        # Проверить, был ли указан параметр --editor при запуске утилиты
        if self._cl_params.editor:
            return self._cl_params.editor.strip()

        # Проверить, запущено ли приложение в сеансе X
        if os.getenv("DISPLAY"):
            # Проверить, установлена ли переменная среды VISUAL
            visual = os.getenv("VISUAL")
            if visual:
                return visual

        # Проверить, установлена ли переменная среды EDITOR
        editor = os.getenv("EDITOR")
        if editor:
            return editor

        # Использовать первый из доступных редакторов в следующем порядке: mcedit, nano, vim, vi
        for editor in ["mcedit", "nano", "vim", "vi"]:
            if shutil.which(editor):
                return editor

        # Если ни один из этих шагов не приводит к выбору редактора, то возникает ошибка
        raise FileNotFoundError("Не найден подходящий редактор. Используй параметр --editor для указания редактора.")


app = App()
