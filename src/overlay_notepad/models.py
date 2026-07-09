from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(slots=True)
class NoteEntry:
    """Пара ключ-значение, прочитанная из файла."""

    key: str
    value: str

    @classmethod
    def from_mapping(cls, mapping: dict[str, str]) -> NoteEntry:
        key, value = next(iter(mapping.items()))
        return cls(key=key, value=value)


class NoteCollection:
    """Упрощённый контейнер для списка NoteEntry."""

    def __init__(self, entries: Iterable[NoteEntry] | None = None) -> None:
        """Создаёт коллекцию с опциональным списком заметок."""
        self._entries: list[NoteEntry] = list(entries or [])

    def __iter__(self):
        """Возвращает итератор по заметкам."""
        return iter(self._entries)

    def __len__(self) -> int:
        """Количество элементов в коллекции."""
        return len(self._entries)

    def __getitem__(self, item: int) -> NoteEntry:
        """Достаёт запись по индексу."""
        return self._entries[item]

    def replace_all(self, entries: Iterable[NoteEntry]) -> None:
        """Полностью заменяет содержимое коллекции."""
        self._entries = list(entries)
