#!/usr/bin/env python3
"""
__file__ = 'sstring.py'

Основные классы:

- `SString`: Класс SString расширяет стандартный строковый тип, предоставляя возможность отслеживать максимальную
             длину строк для всех объектов входящих в одну группу.
"""
from typing import Optional, final
from threading import Lock


@final
class SString(str):
    """
    Класс SString расширяет стандартный строковый тип, предоставляя
    возможность отслеживать максимальную длину строк для всех объектов входящих в одну группу.

    Каждый экземпляр SString ассоциируется с группой (по умолчанию 'default'),
    и при создании нового экземпляра, класс автоматически обновляет и сохраняет
    максимальную длину строки для этой группы. Длина может быть задана явно
    через параметр extraLength или определяться как длина переданного текста.

    Атрибуты:
        __maxCustomLength (dict): Словарь, хранящий максимальную длину строки
                                  для каждой группы.

    Методы:
        __new__(cls, text: str, group: Optional[str] = "default", extraLength: Optional[int] = None):
            Конструктор класса.

    Свойства:
        max_length (int): Возвращает максимальную длину строки для группы,
                          к которой принадлежит экземпляр.

    Пример использования:
        >>> s1 = SString("Hello", group="g1")
        >>> s2 = SString("World!", group="g1", extraLength=10)
        >>> s1.max_length
        10
        >>> s3 = SString("Short", group="g2")
        >>> s3.max_length
        5
    """

    # Аннотация типа для атрибута экземпляра
    # без этого Pylance будет ругаться
    __group: str

    __maxCustomLength: dict = {}

    __lock = Lock()  # Для обеспечения потокобезопасности

    def __new__(cls, text: str, group: str = "default", extraLength: Optional[int] = None):
        """
        Создание экземпляра MemberString.

        Args:
            text (str): Текстовое значение для экземпляра.
            group (Optional[str]): Идентификатор группы для изолированного отслеживания максимальной длины.
            extraLength (Optional[int]): Дополнительное числовое значение для внутреннего использования.

        Returns:
            MemberString: Новый экземпляр класса MemberString.
        """
        # Создание экземпляра str
        obj = str.__new__(cls, text)
        # Инициализация дополнительных атрибутов

        obj.__group = group  # Сохранение идентификатор группы в экземпляре

        # Инициализация и обновление максимальной длины для группы
        length = extraLength if extraLength is not None else len(text)
        with cls.__lock:
            cls.__maxCustomLength[group] = max(cls.__maxCustomLength.get(group, -1), length)

        return obj

    @property
    def max_length(self) -> int:
        """
        Получение максимальной длины для группы к которой относится экземпляр.

        Returns:
            int: Максимальное значение длины среди всех экземпляров в той же группе.
        """
        return type(self).__maxCustomLength.get(self.__group, -1)

    @property
    def group(self) -> str:
        """Возвращает группу, к которой принадлежит экземпляр."""
        return self.__group

    @classmethod
    def unify_groups_lengths(cls, *args: str) -> None:
        """
        Ищет максимальную длину среди указанных групп, и затем применяет ее ко всем этим группам.
        """

        # итерирует по args, для каждого элемента a получает значение из cls.__maxCustomLength
        # с ключом a (или -1, если такого ключа нет), и собирает эти значения в список
        max_ = max(cls.__maxCustomLength.get(a, -1) for a in args)

        with cls.__lock:
            # для каждого элемента a в args он устанавливает значение max_ в
            # cls.__maxCustomLength[a]. Использование метода update с генератором пар ключ-значение
            cls.__maxCustomLength.update((a, max_) for a in args)


if __name__ == "__main__":
    pass
