from collections.abc import Iterator
import json
from pathlib import Path

from .models import NoteCollection, NoteEntry


class DataStore:
    """Инкапсулирует чтение и фильтрацию данных из файла."""

    def __init__(self, file_path: Path) -> None:
        """Создаёт стор с указанным файлом."""
        self.file_path = file_path
        self.entries = NoteCollection()

    def set_file_path(self, file_path: Path) -> None:
        """Обновляет путь к файлу."""
        self.file_path = file_path

    def load(self) -> None:
        """Перечитывает файл и обновляет entries."""
        self.entries.replace_all(self._iter_entries())

    def find(self, needle: str) -> list[NoteEntry]:
        needle_lower = needle.lower()
        return [
            entry
            for entry in self.entries
            if needle_lower in entry.key.lower()
        ]

    def all_entries(self) -> list[NoteEntry]:
        return list(self.entries)

    def _iter_entries(self) -> Iterator[NoteEntry]:
        if not self.file_path.exists():
            return iter(())
        with self.file_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    yield NoteEntry.from_mapping(data)
                except (json.JSONDecodeError, StopIteration):
                    continue
