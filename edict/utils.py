"""Utilities."""
from __future__ import annotations

from typing import Any, Generic, Iterable, Iterator, Optional, TypeVar

T = TypeVar("T")


class OrderedSet(Generic[T]):
    def __init__(self, elems: Optional[Iterable[T]] = None):
        if elems is None:
            self._data = {}
        else:
            self._data = {x: None for x in elems}

    def __eq__(self, other: Any):
        if isinstance(other, OrderedSet):
            return self._data == other._data
        return NotImplemented

    def __contains__(self, item: Any) -> bool:
        return item in self._data

    def __iter__(self) -> Iterator[T]:
        return iter(self._data.keys())

    def __len__(self) -> int:
        return len(self._data)

    def add(self, elem: T) -> None:
        self._data[elem] = None

    def update(self, *others: Iterable[T]) -> None:
        for other in others:
            for key in other:
                self._data[key] = None

    def clear(self) -> None:
        self._data.clear()
