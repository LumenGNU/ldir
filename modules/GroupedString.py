#!/usr/bin/env python3
"""
__file__ = 'GroupedString.py'


"""
from __future__ import annotations
from typing import Final, final, Annotated
from threading import RLock
from weakref import WeakSet


@final
class GroupedString:
    """Класс для управления строками с группировкой и отслеживанием максимальной длины строки в группе.

    Пример использования:

    ```python
    from operator import iadd, isub, mod
    import random
    import string
    import sys
    import os
    import requests
    sys.path.append(os.path.abspath('..'))
    from modules.GroupedString import GroupedString


    def user_string(count:int):

        url = "https://randomuser.me/api/"
        params = {
            "results": count,  # Количество пользователей
            "nat": "ch",  # Национальность
            "inc": "name,email,phone"  # Включаемые поля
        }

        attempt_count = 5

        while attempt_count:
            try:
                response = requests.get(url, params=params)
                response.raise_for_status()  # Проверка на ошибки HTTP
                data = response.json()
                break  # Выход из цикла при успешном получении данных
            except requests.RequestException as e:
                attempt_count = isub(attempt_count, 1)
                print(f"Ошибка при запросе данных: {e}.\\nПопытка повторного подключения.", file=sys.stderr)
                if not attempt_count:
                    raise requests.RequestException from e


        data = response.json()

        for user in data['results']:
            yield f"{user['name']['first']} {user['name']['last']}", user['email'],  user['phone']

    def create_and_print_table(rows):
        table = []
        for i in range(3):
            for s in user_string(rows):
                row = [
                    GroupedString(s[0], f"{i}Column1"),
                    GroupedString(s[1], f"{i}Column2"),
                    GroupedString(s[2], f"{i}Column3")
                ]
                table.append(row)

        # Вывод таблицы с соответствующим выравниванием
        for i, row in enumerate(table):
            formatted_row = [
                row[0].ljust_text,  # Выравнивание вправо для первой колонки
                row[1].ljust_text,  # Выравнивание влево для второй колонки
                row[2].ljust_text  # Центрирование для третьей колонки
            ]
            if not mod(i, rows):
                print(' ')
            print("|"," | ".join(formatted_row),"|")

        pass

    # Количество строк
    rows = 5


    # Создание и вывод таблицы пользовательских данных.
    # Используется для демонстрации работы форматирования вывода.
    create_and_print_table(rows)
    pass
    ```

    Возможный вывод:

    ```out
    | Marie Mathieu       | marie.mathieu@example.com       | 079 534 93 60 |
    | Marianne Carpentier | marianne.carpentier@example.com | 077 457 44 55 |
    | Dino Girard         | dino.girard@example.com         | 077 838 99 00 |
    | Ruth Girard         | ruth.girard@example.com         | 077 701 45 91 |
    | Paul Aubert         | paul.aubert@example.com         | 077 124 18 64 |

    | Adrienne Rolland | adrienne.rolland@example.com | 077 144 51 72 |
    | Aylin Thomas     | aylin.thomas@example.com     | 075 044 53 62 |
    | Marietta Aubert  | marietta.aubert@example.com  | 076 822 37 17 |
    | Jacques Muller   | jacques.muller@example.com   | 075 057 72 31 |
    | Liana Lemoine    | liana.lemoine@example.com    | 078 941 83 23 |

    | Enes Bourgeois   | enes.bourgeois@example.com   | 077 323 90 15 |
    | Mirjam Noel      | mirjam.noel@example.com      | 076 872 23 92 |
    | Dominic Arnaud   | dominic.arnaud@example.com   | 079 530 40 69 |
    | Carmen Blanchard | carmen.blanchard@example.com | 077 932 24 27 |
    | Aylin Philippe   | aylin.philippe@example.com   | 078 888 01 00 |
    ```




    """

    __lock: Final = RLock()  # Для обеспечения потокобезопасности # pylint: disable=invalid-name

    __instances: Final[dict[str, WeakSet[GroupedString]]] = {}  # pylint: disable=invalid-name

    __max_length: Final[dict[str, int]] = {}  # pylint: disable=invalid-name

    def __init__(self, text: str = "", group: str = "default", /) -> None:
        self.__text: str = ""
        self.__group = group

        # Добавление текущего экземпляра в набор экземпляров класса
        with type(self).__lock:
            # Проверка, существует ли уже WeakSet для группы
            if self.group not in type(self).__instances:
                type(self).__instances[self.group] = WeakSet()
            # Добавление экземпляра в WeakSet для данной группы
            type(self).__instances[self.group].add(self)

        self.text = text

    @property
    def value(self) -> tuple[Annotated[str, "text"], Annotated[int, "padding"]]:
        """
        Возвращает текст и количество символов, необходимых для выравнивания текста в рамках его группы.

        Returns:
            tuple[str, int]: Кортеж, содержащий текст экземпляра и дополнительное количество символов.
        """
        return self.text, self.text_padding_length - len(self.text)

    @property
    def text(self) -> str:
        """
        Текст экземпляра.
        """
        return self.__text

    @text.setter
    def text(self, text: str) -> None:
        self.__text = text
        self.update_max_length_for_group(self.group)

    @property
    def ljust_text(self) -> str:
        """
        Возвращает текст, выровненный по левому краю, дополненный пробелами до максимальной длины в группе.

        Returns:
            str: Текст, выровненный по левому краю.
        """
        return self.text.ljust(self.text_padding_length)

    @property
    def rjust_text(self) -> str:
        """
        Возвращает текст, выровненный по правому краю, дополненный пробелами до максимальной длины в группе.

        Returns:
            str: Текст, выровненный по правому краю.
        """
        return self.text.rjust(self.text_padding_length)

    @property
    def center_text(self) -> str:
        """
        Возвращает текст, центрированный, дополненный пробелами до максимальной длины в группе.

        Returns:
            str: Центрированный текст.
        """
        return self.text.center(self.text_padding_length)

    @property
    def group(self) -> str:
        """Группа, к которой принадлежит экземпляр."""
        return self.__group

    @group.setter
    def group(self, new_group: str) -> None:
        """
        Изменяет группу, к которой принадлежит экземпляр, обновляя все необходимые ссылки
        и пересчитывая максимальные длины для новой и старой группы.

        Args:
            new_group (str): Новая группа для этого экземпляра.
        """
        old_group = self.__group
        if old_group == new_group:
            return  # Если группа не изменяется, ничего не делаем.

        with type(self).__lock:
            # Удаляем экземпляр из старой группы.
            type(self).__instances[old_group].discard(self)

            if not type(self).__instances[old_group]:
                # Если старая группа теперь пуста, удаляем её.
                del type(self).__instances[old_group]
                del type(self).__max_length[old_group]
            else:
                # Пересчитываем максимальную длину для старой группы.
                self.update_max_length_for_group(old_group)

            # Добавляем экземпляр в новую группу.
            self.__group = new_group
            if new_group not in type(self).__instances:
                type(self).__instances[new_group] = WeakSet()
            type(self).__instances[new_group].add(self)

            # Пересчитываем максимальную длину для новой группы.
            self.update_max_length_for_group(new_group)

    @classmethod
    def update_max_length_for_group(cls, group: str) -> None:
        """Пересчитать максимальной длины для группы"""
        with cls.__lock:
            if not cls.__instances[group]:
                # удалить групу из cls.__instances и cls.__max_length
                del cls.__instances[group]
                del cls.__max_length[group]
            cls.__max_length[group] = max(
                (len(GroupedString.text) for GroupedString in cls.__instances[group]), default=0
            )

    @property
    def text_padding_length(self) -> int:
        """
        Получение максимальной длины для группы к которой относится экземпляр.

        Returns:
            int: Максимальное значение длины среди всех экземпляров в той же группе.
        """
        with type(self).__lock:
            return type(self).__max_length.get(self.group, -1)

    @classmethod
    def text_padding_length_for_group(cls, group: str) -> int:
        """
        Возвращает максимальную длину текста в указанной группе.

        Args:
            group (str): Название группы.

        Returns:
            int: Максимальная длина текста в группе.
        """
        with cls.__lock:
            return cls.__max_length.get(group, -1)

    @classmethod
    def unify_lengths_for_groups(cls, *args: str) -> None:
        """Устанавливает максимальную длину текста для всех указанных групп равной максимальной длине среди них."""
        with cls.__lock:
            max_ = max(cls.__max_length.get(group, -1) for group in args)
            cls.__max_length.update((group, max_) for group in args)

    def __del__(self) -> None:
        with type(self).__lock:
            group_set = self.__instances[self.group]
            group_set.discard(self)
            if not group_set:
                del self.__instances[self.group]
                del self.__max_length[self.group]
            else:
                self.update_max_length_for_group(self.group)

    @classmethod
    def get_instances_len_all(cls) -> int:
        """
        Возвращает общее количество экземпляров во всех группах.

        Returns:
            int: Общее количество экземпляров.
        """
        return sum(len(weak_set) for weak_set in cls.__instances.values())

    @classmethod
    def get_instances_len_for_group(cls, group: str) -> int:
        """
        Возвращает количество экземпляров в указанной группе.

        Args:
            group (str): Название группы.

        Returns:
            int: Количество экземпляров в группе.
        """
        return len(cls.__instances[group])


if __name__ == "__main__":
    pass
