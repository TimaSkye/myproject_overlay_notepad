"""Менеджер настроек и модель конфигурации."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from PySide6 import QtCore


DEFAULT_ROW_HEIGHT = 28
DEFAULT_FONT_PT = 11
DEFAULT_FONT_FAMILY = "Segoe UI"
DEFAULT_OPACITY = 200  # 0-255
DEFAULT_BACKGROUND_COLOR = "#141414"
DEFAULT_TEXT_COLOR = "#FFFFFF"


@dataclass(slots=True)
class AppSettings:
    """Хранит путь к файлу, позицию и параметры UI."""

    file_path: Path
    position: QtCore.QPoint
    size: QtCore.QSize
    row_height: int = DEFAULT_ROW_HEIGHT
    font_pt: int = DEFAULT_FONT_PT
    font_family: str = DEFAULT_FONT_FAMILY
    background_color: str = DEFAULT_BACKGROUND_COLOR
    text_color: str = DEFAULT_TEXT_COLOR
    background_opacity: int = DEFAULT_OPACITY
    auto_launch: bool = False


class SettingsManager:
    """Читает и сохраняет настройки в JSON-файл."""

    def __init__(self, config_path: Path) -> None:
        """Фиксирует путь к конфигурационному файлу."""
        self.config_path = config_path

    def has_config(self) -> bool:
        return self.config_path.exists()

    def load(
        self,
        fallback_file: Path,
        fallback_position: QtCore.QPoint,
        fallback_size: QtCore.QSize,
    ) -> AppSettings:
        data: dict[str, object] = {}
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                data = {}

        file_value = Path(data.get("file_path", str(fallback_file)))
        position_data = data.get("position", {}) if isinstance(data, dict) else {}
        if not isinstance(position_data, dict):
            position_data = {}
        x_value = int(position_data.get("x", fallback_position.x()))
        y_value = int(position_data.get("y", fallback_position.y()))

        size_data = data.get("size", {}) if isinstance(data, dict) else {}
        if not isinstance(size_data, dict):
            size_data = {}
        width = int(size_data.get("width", fallback_size.width()))
        height = int(size_data.get("height", fallback_size.height()))

        ui_data = data.get("ui", {}) if isinstance(data, dict) else {}
        if not isinstance(ui_data, dict):
            ui_data = {}
        row_height = int(ui_data.get("row_height", DEFAULT_ROW_HEIGHT))
        font_pt = int(ui_data.get("font_pt", DEFAULT_FONT_PT))
        font_family = str(ui_data.get("font_family", DEFAULT_FONT_FAMILY))
        background_color = str(ui_data.get("background_color", DEFAULT_BACKGROUND_COLOR))
        text_color = str(ui_data.get("text_color", DEFAULT_TEXT_COLOR))
        background_opacity = int(ui_data.get("background_opacity", DEFAULT_OPACITY))
        auto_launch = bool(data.get("auto_launch", False))

        return AppSettings(
            file_path=file_value,
            position=QtCore.QPoint(x_value, y_value),
            size=QtCore.QSize(width, height),
            row_height=row_height,
            font_pt=font_pt,
            font_family=font_family,
            background_color=background_color,
            text_color=text_color,
            background_opacity=background_opacity,
            auto_launch=auto_launch,
        )

    def save(self, config: AppSettings) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "file_path": str(config.file_path),
            "position": {"x": config.position.x(), "y": config.position.y()},
            "size": {"width": config.size.width(), "height": config.size.height()},
            "ui": {
                "row_height": config.row_height,
                "font_pt": config.font_pt,
                "font_family": config.font_family,
                "background_color": config.background_color,
                "text_color": config.text_color,
                "background_opacity": config.background_opacity,
            },
            "auto_launch": config.auto_launch,
        }
        self.config_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
