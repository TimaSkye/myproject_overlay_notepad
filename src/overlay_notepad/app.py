import argparse
from dataclasses import replace
from pathlib import Path
import subprocess
import sys

from PySide6 import QtCore, QtGui, QtWidgets

from .data_store import DataStore
from .settings import AppSettings, SettingsManager
from .ui.about_dialog import AboutDialog
from .ui.overlay_widget import OverlayWidget
from .ui.settings_dialog import SettingsDialog


DEFAULT_POSITION = QtCore.QPoint(100, 100)
DEFAULT_SIZE = QtCore.QSize(320, 64)
ICON_PATH = Path(__file__).resolve().parent.parent / "icon.ico"
ABOUT_IMAGE_PATH = Path(__file__).resolve().parent.parent / "notepad.png"
DONATION_QR_PATH = Path(__file__).resolve().parent.parent / "qr.jfif"


class OverlayApplication(QtWidgets.QApplication):
    """Qt-приложение Overlay Notepad, которое управляет настройками и виджетом."""

    def __init__(
        self,
        start_file: Path,
        config_path: Path,
        force_setup: bool = False,
        cli_override: bool = False,
    ) -> None:
        """Настраивает приложение, загружает конфиг и поднимает UI."""
        super().__init__([])
        self.setQuitOnLastWindowClosed(False)
        self._icon = QtGui.QIcon(str(ICON_PATH)) if ICON_PATH.exists() else QtGui.QIcon()
        if not self._icon.isNull():
            self.setWindowIcon(self._icon)
        self.tray_icon: QtWidgets.QSystemTrayIcon | None = None
        self.tray_menu: QtWidgets.QMenu | None = None
        self.settings_manager = SettingsManager(config_path=config_path)
        config_exists = self.settings_manager.has_config()
        if config_exists:
            self.config = self.settings_manager.load(
                fallback_file=start_file,
                fallback_position=DEFAULT_POSITION,
                fallback_size=DEFAULT_SIZE,
            )
        else:
            self.config = AppSettings(
                file_path=start_file,
                position=QtCore.QPoint(DEFAULT_POSITION),
                size=QtCore.QSize(DEFAULT_SIZE),
            )
        if cli_override:
            self.config.file_path = start_file

        needs_initial_dialog = force_setup or not config_exists
        if needs_initial_dialog:
            self.config = self._prompt_initial_settings(self.config)

        self._ensure_file(self.config.file_path)
        self.settings_manager.save(self.config)

        self.store = DataStore(file_path=self.config.file_path)
        self.widget = OverlayWidget(
            self.store,
            row_height=self.config.row_height,
            font_pt=self.config.font_pt,
            font_family=self.config.font_family,
            background_color=self.config.background_color,
            text_color=self.config.text_color,
            background_opacity=self.config.background_opacity,
        )
        if not self._icon.isNull():
            self.widget.setWindowIcon(self._icon)
        self.widget.entry_copied.connect(self._on_entry_copied)
        self.widget.request_settings.connect(self._open_settings_dialog)
        self.widget.request_open_file.connect(self._open_file_in_editor)
        self.widget.request_about.connect(self._open_about_dialog)
        self.widget.position_changed.connect(self._on_position_changed)
        self._orig_resize_event = self.widget.resizeEvent
        self.widget.resizeEvent = self._on_resize_event

        self.file_watcher = QtCore.QFileSystemWatcher()
        self.file_watcher.fileChanged.connect(self._on_file_changed)
        self._watch_file(self.config.file_path)

        self.widget.setWindowTitle("Overlay Notepad")
        self.widget.apply_geometry(self.config.position, self.config.size)
        self.widget.show()
        self._init_tray_icon()
        self.aboutToQuit.connect(self._cleanup_tray_icon)

    def _on_file_changed(self, path: str) -> None:
        self.widget.reload_entries()
        self.widget.refresh_view()
        self._watch_file(self.config.file_path)

    def _on_entry_copied(self, value: str) -> None:
        self.widget.setToolTip(f"Скопировано: {value}")

    def _open_settings_dialog(self) -> None:
        dialog = SettingsDialog(self.widget)
        if not self._icon.isNull():
            dialog.setWindowIcon(self._icon)
        dialog.set_values(self.config)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            new_config = dialog.get_settings()
            self._apply_new_config(new_config)

    def _init_tray_icon(self) -> None:
        icon = self._icon if not self._icon.isNull() else self.widget.windowIcon()
        self.tray_icon = QtWidgets.QSystemTrayIcon(icon, self)
        self.tray_menu = QtWidgets.QMenu()

        show_action = self.tray_menu.addAction("Показать окно")
        show_action.triggered.connect(self._bring_to_front)

        open_file_action = self.tray_menu.addAction("Открыть файл…")
        open_file_action.triggered.connect(self._open_file_in_editor)

        settings_action = self.tray_menu.addAction("Настройки…")
        settings_action.triggered.connect(self._open_settings_dialog)

        about_action = self.tray_menu.addAction("О программе…")
        about_action.triggered.connect(self._open_about_dialog)

        quit_action = self.tray_menu.addAction("Выход")
        quit_action.triggered.connect(QtWidgets.QApplication.quit)

        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.setToolTip("Overlay Notepad")
        self.tray_icon.show()

    def _on_tray_activated(self, reason: QtWidgets.QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QtWidgets.QSystemTrayIcon.ActivationReason.Trigger,
            QtWidgets.QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._bring_to_front()

    def _bring_to_front(self) -> None:
        if self.widget.isHidden():
            self.widget.show()
        self.widget.raise_()
        self.widget.activateWindow()

    def _cleanup_tray_icon(self) -> None:
        if self.tray_icon:
            self.tray_icon.hide()
            self.tray_icon.setContextMenu(None)
            self.tray_icon.deleteLater()
            self.tray_icon = None
        if self.tray_menu:
            self.tray_menu.deleteLater()
            self.tray_menu = None

    def _open_file_in_editor(self) -> None:
        try:
            subprocess.Popen(["notepad.exe", str(self.config.file_path)], shell=False)
        except OSError:
            QtWidgets.QMessageBox.warning(
                self.widget,
                "Overlay Notepad",
                "Не удалось запустить Блокнот. Убедитесь, что notepad.exe доступен.",
            )

    def _open_about_dialog(self) -> None:
        image_path = ABOUT_IMAGE_PATH if ABOUT_IMAGE_PATH.exists() else None
        app_icon = self._icon if not self._icon.isNull() else None
        donation_qr = DONATION_QR_PATH if DONATION_QR_PATH.exists() else None
        dialog = AboutDialog(
            self.widget,
            image_path=image_path,
            donation_qr_path=donation_qr,
            app_icon=app_icon,
        )
        dialog.exec()

    def _prompt_initial_settings(self, current: AppSettings) -> AppSettings:
        dialog = SettingsDialog()
        dialog.set_values(current)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            return dialog.get_settings()
        return current

    def _apply_new_config(self, new_config: AppSettings) -> None:
        self._ensure_file(new_config.file_path)
        self.config = new_config
        self.store.set_file_path(new_config.file_path)
        self.widget.update_preferences(
            row_height=new_config.row_height,
            font_pt=new_config.font_pt,
            font_family=new_config.font_family,
            background_color=new_config.background_color,
            text_color=new_config.text_color,
            background_opacity=new_config.background_opacity,
        )
        self.widget.apply_geometry(new_config.position, new_config.size)
        self.widget.reload_entries()
        self.widget.refresh_view()
        self._watch_file(new_config.file_path)
        self.settings_manager.save(self.config)
        self._configure_auto_launch(new_config.auto_launch)

    def _configure_auto_launch(self, enabled: bool) -> None:
        if sys.platform != "win32":
            return
        import winreg

        run_key = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_key, 0, winreg.KEY_ALL_ACCESS) as key:
            app_path = str(Path(sys.argv[0]).resolve())
            value_name = "OverlayNotepad"
            if enabled:
                winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, app_path)
            else:
                try:
                    winreg.DeleteValue(key, value_name)
                except FileNotFoundError:
                    pass

    def _watch_file(self, file_path: Path) -> None:
        if not self.file_watcher:
            return
        if self.file_watcher.files():
            self.file_watcher.removePaths(self.file_watcher.files())
        if file_path.exists():
            self.file_watcher.addPath(str(file_path))

    def _on_position_changed(self, position: QtCore.QPoint) -> None:
        self._update_geometry(position=position)

    def _on_resize_event(self, event: QtGui.QResizeEvent) -> None:  # noqa: N802
        if self._orig_resize_event:
            self._orig_resize_event(event)
        self._update_geometry()

    def _update_geometry(self, position: QtCore.QPoint | None = None) -> None:
        new_position = position or self.widget.pos()
        new_size = self.widget.size()
        self.config = replace(self.config, position=new_position, size=new_size)
        self.settings_manager.save(self.config)

    def _ensure_file(self, file_path: Path) -> None:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if not file_path.exists():
            file_path.write_text('{"demo":"значение"}\n', encoding="utf-8")


def run_app(file_path: Path, config_path: Path, force_setup: bool, cli_override: bool = False) -> int:
    """Создаёт OverlayApplication и запускает цикл Qt."""
    app = OverlayApplication(
        start_file=file_path,
        config_path=config_path,
        force_setup=force_setup,
        cli_override=cli_override,
    )
    return app.exec()


def _default_base_dir() -> Path:
    """Определяет директорию, в которой по умолчанию лежат file.txt и settings.json."""
    try:
        entry = Path(sys.argv[0]).resolve()
    except OSError:
        entry = Path()
    if entry.exists():
        return entry.parent if entry.is_file() else entry
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd()


def parse_args() -> argparse.Namespace:
    """Парсит аргументы командной строки."""
    base_dir = _default_base_dir()
    parser = argparse.ArgumentParser(description="Overlay Notepad — оверлей с парами ключ-значение")
    parser.add_argument(
        "--file",
        type=Path,
        default=base_dir / "file.txt",
        help="Путь к источнику данных (по умолчанию file.txt рядом с исполняемым файлом)",
    )
    parser.add_argument(
        "--config-file",
        type=Path,
        default=base_dir / "settings.json",
        help="Путь к JSON с настройками (по умолчанию settings.json рядом с исполняемым файлом)",
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Запуск в режиме новой настройки (диалог перед стартом)",
    )
    return parser.parse_args()


def main() -> int:
    """Точка входа при запуске из Python."""
    args = parse_args()
    file_path: Path = args.file or Path("file.txt")
    return run_app(
        file_path=file_path,
        config_path=args.config_file,
        force_setup=bool(args.setup),
        cli_override=bool(args.file),
    )


if __name__ == "__main__":
    raise SystemExit(main())
