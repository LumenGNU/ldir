#!/usr/bin/env python3
""""""


from __future__ import annotations
from typing import Final, List, Literal, TypeAlias, TypedDict


VALID_SORT_OPTIONS: Final = ["none", "name", "iname", "type", "mime"]
SortTypeLiteral: TypeAlias = Literal["none", "name", "iname", "type", "mime"]


class Configs(TypedDict):
    depth: int
    subdirectories: bool
    hidden: bool
    sort: SortTypeLiteral
    filters: List[str]


if __name__ == "__main__":
    pass
