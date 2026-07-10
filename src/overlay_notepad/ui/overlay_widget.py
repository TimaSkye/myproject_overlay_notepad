import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import sys

from PySide6 import QtCore, QtGui, QtWidgets

from ..data_store import DataStore
from ..models import NoteEntry
from ..settings import DEFAULT_FONT_FAMILY, DEFAULT_FONT_PT, DEFAULT_ROW_HEIGHT


SCROLL_STEP = 1
EVENT_SYSTEM_FOREGROUND = 0x0003
WINEVENT_OUTOFCONTEXT = 0x0000
WINEVENT_SKIPOWNPROCESS = 0x0002
HWINEVENTHOOK = wintypes.HANDLE
WM_WINDOWPOSCHANGING = 0x0046
WM_WINDOWPOSCHANGED = 0x0047
WM_ACTIVATE = 0x0006
WM_ACTIVATEAPP = 0x001C
GWLP_WNDPROC = -4

LONG_PTR = (
    ctypes.c_longlong
    if ctypes.sizeof(ctypes.c_void_p) == ctypes.sizeof(ctypes.c_longlong)
    else ctypes.c_long
)
LRESULT = LONG_PTR
ShellHookMsgId = ctypes.windll.user32.RegisterWindowMessageW("SHELLHOOK")  # type: ignore[attr-defined]


class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class _MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", _POINT),
        ("lPrivate", wintypes.DWORD),
    ]


@dataclass(slots=True)
class DisplayState:
    """Текущее состояние списка (первый индекс + фильтр)."""

    offset: int = 0
    filter_text: str = ""


class OverlayWidget(QtWidgets.QWidget):
    """Каркас окна Overlay Notepad: выводит пары и обрабатывает hover/scroll/click."""

    entry_copied = QtCore.Signal(str)
    request_settings = QtCore.Signal()
    request_open_file = QtCore.Signal()
    request_about = QtCore.Signal()
    position_changed = QtCore.Signal(QtCore.QPoint)

    def __init__(
        self,
        store: DataStore,
        *,
        row_height: int = DEFAULT_ROW_HEIGHT,
        font_pt: int = DEFAULT_FONT_PT,
        font_family: str = DEFAULT_FONT_FAMILY,
        background_color: str = "#141414",
        text_color: str = "#FFFFFF",
        background_opacity: int = 200,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        """Создаёт окно-оверлей и связывает его с источником данных."""
        super().__init__(parent)
        self.store = store
        self.state = DisplayState()
        self.entries: list[NoteEntry] = []
        self.filtered_entries: list[NoteEntry] = []
        self.move_mode = False
        self._drag_offset = QtCore.QPoint()
        self.search_buffer = ""
        self.search_active = False
        self.visible_rows = 0
        self.row_height = max(10, row_height)
        self.font_pt = max(1, font_pt)
        self.font_family = font_family
        self.background_color = QtGui.QColor(background_color)
        self.text_color = QtGui.QColor(text_color)
        self.background_opacity = max(0, min(255, background_opacity))
        self._win_event_hook: int | None = None
        self._win_event_proc = None
        self._old_wndproc: int | None = None
        self._wndproc_cb = None
        self._shell_hook_registered = False

        self.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.WindowStaysOnTopHint
            | QtCore.Qt.WindowType.NoDropShadowWindowHint
            | QtCore.Qt.WindowType.Tool
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating, False)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        font = QtGui.QFont(self.font_family, 9)
        self.setFont(font)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(8, 4, 8, 4)
        self.layout.setSpacing(0)

        self.label_widgets: list[QtWidgets.QLabel] = []
        self.filter_label = QtWidgets.QLabel(self)
        self.filter_label.setStyleSheet(
            "color: rgba(255,255,255,180); background-color: rgba(0,0,0,100); "
            "padding: 2px 6px; border-radius: 3px; font-size: 9pt;"
        )
        self.filter_label.hide()
        self._ensure_row_count(2)

        self._context_menu = self._build_context_menu()
        self._topmost_timer = QtCore.QTimer(self)
        self._topmost_timer.setInterval(300)
        self._topmost_timer.timeout.connect(self._ensure_topmost)
        self._topmost_timer.start()
        self._install_foreground_hook()
        self.setMouseTracking(True)

        self.reload_entries()
        self._update_visible_rows()
        self._apply_palette()

    def showEvent(self, event: QtGui.QShowEvent) -> None:  # noqa: N802
        super().showEvent(event)
        self._install_wndproc_hook()
        self._register_shell_hook()
        self._ensure_topmost()

    def changeEvent(self, event: QtCore.QEvent) -> None:  # noqa: N802
        super().changeEvent(event)
        if event.type() == QtCore.QEvent.Type.ActivationChange:
            self._ensure_topmost()

    def _create_label(self) -> QtWidgets.QLabel:
        label = QtWidgets.QLabel()
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.NoTextInteraction)
        label.setStyleSheet("color: white; background-color: rgba(20,20,20,180); padding: 2px 4px;")
        return label

    def _build_context_menu(self) -> QtWidgets.QMenu:
        menu = QtWidgets.QMenu(self)
        move_action = menu.addAction("Переместить окно")
        move_action.triggered.connect(lambda _checked=False: self._enable_move_mode())

        open_file_action = menu.addAction("Открыть файл…")
        open_file_action.triggered.connect(lambda _checked=False: self.request_open_file.emit())

        settings_action = menu.addAction("Настройки…")
        settings_action.triggered.connect(lambda _checked=False: self.request_settings.emit())

        about_action = menu.addAction("О программе…")
        about_action.triggered.connect(lambda _checked=False: self.request_about.emit())

        exit_action = menu.addAction("Выход")
        exit_action.triggered.connect(QtWidgets.QApplication.quit)
        return menu

    def enterEvent(self, event: QtCore.QEvent) -> None:  # noqa: N802 (Qt naming)
        self.search_active = True
        self.setFocus()
        self._update_filter_label()
        super().enterEvent(event)

    def leaveEvent(self, event: QtCore.QEvent) -> None:  # noqa: N802
        self.search_active = False
        self.search_buffer = ""
        self.state.filter_text = ""
        self._apply_state()
        self.filter_label.hide()
        super().leaveEvent(event)

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:  # noqa: N802
        if self.move_mode:
            event.ignore()
            return
        delta = event.angleDelta().y()
        direction = -1 if delta > 0 else 1
        self.state.offset = max(0, self.state.offset + direction * SCROLL_STEP)
        self._apply_state()
        event.accept()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            if self.move_mode:
                self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            else:
                index = self._index_from_position(event.position().y())
                entry = self._entry_for_row(index)
                if entry:
                    QtGui.QGuiApplication.clipboard().setText(entry.value)
                    self.entry_copied.emit(entry.value)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        if self.move_mode and event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            target = event.globalPosition().toPoint() - self._drag_offset
            self.move(target)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        if self.move_mode and event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._disable_move_mode()
            self.position_changed.emit(self.pos())
            self._ensure_topmost()
        super().mouseReleaseEvent(event)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # noqa: N802
        self._remove_foreground_hook()
        self._remove_wndproc_hook()
        self._unregister_shell_hook()
        super().closeEvent(event)

    def nativeEvent(self, eventType: bytes, message: int) -> tuple[bool, int]:  # noqa: N802
        if sys.platform == "win32" and eventType == b"windows_generic_MSG" and message:
            msg = ctypes.cast(message, ctypes.POINTER(_MSG)).contents
            if msg.message == ShellHookMsgId:
                QtCore.QTimer.singleShot(0, self._ensure_topmost)
                return True, 0
        return super().nativeEvent(eventType, message)

    def contextMenuEvent(self, event: QtGui.QContextMenuEvent) -> None:  # noqa: N802
        self._context_menu.exec(event.globalPos())
        event.accept()

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:  # noqa: N802
        if not self.search_active:
            super().keyPressEvent(event)
            return

        if event.key() in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter):
            event.accept()
            return

        if event.key() == QtCore.Qt.Key.Key_Escape:
            self.search_buffer = ""
            self.state.filter_text = ""
            self._apply_state()
            event.accept()
            return

        if event.key() == QtCore.Qt.Key.Key_Backspace:
            self.search_buffer = self.search_buffer[:-1]
            self._apply_filter_from_buffer()
            event.accept()
            return

        text = event.text()
        if text and text.isprintable():
            self.search_buffer += text
            self._apply_filter_from_buffer()
            event.accept()
            return

        super().keyPressEvent(event)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._update_visible_rows()
        self._update_filter_label_position()

    def reload_entries(self) -> None:
        self.store.load()
        self.entries = self.store.all_entries()
        self.filtered_entries = self.entries

    def refresh_view(self) -> None:
        self._apply_state()

    def apply_geometry(self, position: QtCore.QPoint, size: QtCore.QSize) -> None:
        self.move(position)
        self.setFixedSize(size)
        self._update_visible_rows()
        self._ensure_topmost()

    def update_preferences(
        self,
        *,
        row_height: int,
        font_pt: int,
        font_family: str,
        background_color: str,
        text_color: str,
        background_opacity: int,
    ) -> None:
        self.row_height = max(10, row_height)
        self.font_pt = max(1, font_pt)
        self.font_family = font_family or DEFAULT_FONT_FAMILY
        self.background_color = QtGui.QColor(background_color)
        self.text_color = QtGui.QColor(text_color)
        self.background_opacity = max(0, min(255, background_opacity))
        self._apply_palette()
        self._update_visible_rows()
        self._update_font()

    def _apply_state(self) -> None:
        search = self.state.filter_text.strip()
        if search:
            self.filtered_entries = self.store.find(search)
        else:
            self.filtered_entries = self.entries

        max_offset = max(0, len(self.filtered_entries) - self.visible_rows)
        self.state.offset = min(self.state.offset, max_offset)

        visible_slice = self.filtered_entries[self.state.offset : self.state.offset + self.visible_rows]
        for label, entry in zip(self.label_widgets, visible_slice, strict=False):
            full_text = f"{entry.key} — {entry.value}"
            metrics = label.fontMetrics()
            available_width = label.width() - 6
            if available_width <= 0:
                available_width = self.width() - 12
            available_width = max(10, available_width)
            elided = metrics.elidedText(full_text, QtCore.Qt.TextElideMode.ElideRight, available_width)
            label.setText(elided)
            label.show()
        for label in self.label_widgets[len(visible_slice) :]:
            label.setText("—")

    def _index_from_position(self, y: float) -> int:
        if self.visible_rows <= 0:
            return 0
        row_height = self.height() / self.visible_rows
        return max(0, min(self.visible_rows - 1, int(y // row_height)))

    def _entry_for_row(self, row_index: int) -> NoteEntry | None:
        target_index = self.state.offset + row_index
        if 0 <= target_index < len(self.filtered_entries):
            return self.filtered_entries[target_index]
        return None

    def _apply_filter_from_buffer(self) -> None:
        self.state.filter_text = self.search_buffer
        self.state.offset = 0
        self._apply_state()
        self._update_filter_label()

    def _enable_move_mode(self) -> None:
        self.move_mode = True
        self.setCursor(QtCore.Qt.CursorShape.SizeAllCursor)

    def _disable_move_mode(self) -> None:
        self.move_mode = False
        self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)

    def _update_visible_rows(self) -> None:
        available_height = max(self.height(), self.row_height)
        base_rows = int(available_height / self.row_height) if self.row_height else 1
        target_rows = max(1, base_rows or 1)
        self._ensure_row_count(target_rows)
        self._apply_state()

    def _ensure_row_count(self, count: int) -> None:
        if count <= 0:
            count = 1
        if count == self.visible_rows and self.label_widgets:
            return
        if count > self.visible_rows:
            for _ in range(count - self.visible_rows):
                label = self._create_label()
                self.layout.addWidget(label)
                self.label_widgets.append(label)
        else:
            for _ in range(self.visible_rows - count):
                label = self.label_widgets.pop()
                self.layout.removeWidget(label)
                label.deleteLater()
        self.visible_rows = count
        self._update_font()

    def _update_font(self) -> None:
        if self.visible_rows <= 0 or not self.label_widgets:
            return
        available_height = max(self.height(), self.row_height)
        row_height = available_height / self.visible_rows
        # Пользователь задаёт целевой кегль, но слегка корректируем, если строка совсем мала
        point_size = max(1, min(int(row_height * 0.9), self.font_pt))
        font = QtGui.QFont(self.font_family, point_size)
        for label in self.label_widgets:
            label.setFont(font)
            label.setStyleSheet(
                f"color: {self.text_color.name(QtGui.QColor.NameFormat.HexRgb)};"
                f" background-color: {self._rgba_background()}; padding: 2px 4px;"
            )
        self.setFont(font)

    def _ensure_topmost(self) -> None:
        if sys.platform != "win32":
            return
        hwnd = int(self.winId())
        if not hwnd:
            return
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        HWND_TOPMOST = -1
        HWND_NOTOPMOST = -2
        SWP_NOSIZE = 0x0001
        SWP_NOMOVE = 0x0002
        SWP_NOACTIVATE = 0x0010
        SWP_SHOWWINDOW = 0x0040
        flags = SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE | SWP_SHOWWINDOW
        user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, flags)
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, flags)

    def _install_foreground_hook(self) -> None:
        if sys.platform != "win32" or self._win_event_hook:
            return
        user32 = ctypes.windll.user32

        WinEventProcType = ctypes.WINFUNCTYPE(
            None,
            HWINEVENTHOOK,
            wintypes.DWORD,
            wintypes.HWND,
            wintypes.LONG,
            wintypes.LONG,
            wintypes.DWORD,
            wintypes.DWORD,
        )

        def _callback(_hook, _event, _hwnd, _idObject, _idChild, _eventThread, _eventTime) -> None:
            QtCore.QTimer.singleShot(0, self._ensure_topmost)
            QtCore.QTimer.singleShot(150, self._ensure_topmost)

        self._win_event_proc = WinEventProcType(_callback)
        self._win_event_hook = user32.SetWinEventHook(
            EVENT_SYSTEM_FOREGROUND,
            EVENT_SYSTEM_FOREGROUND,
            0,
            self._win_event_proc,
            0,
            0,
            WINEVENT_OUTOFCONTEXT | WINEVENT_SKIPOWNPROCESS,
        )

    def _remove_foreground_hook(self) -> None:
        if sys.platform != "win32" or not self._win_event_hook:
            return
        ctypes.windll.user32.UnhookWinEvent(self._win_event_hook)
        self._win_event_hook = None
        self._win_event_proc = None

    def _install_wndproc_hook(self) -> None:
        if sys.platform != "win32" or self._old_wndproc:
            return
        hwnd = int(self.winId())
        if not hwnd:
            return
        user32 = ctypes.windll.user32
        WndProcType = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
        user32.SetWindowLongPtrW.restype = LONG_PTR
        user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, LONG_PTR]
        user32.CallWindowProcW.restype = LRESULT
        user32.CallWindowProcW.argtypes = [LONG_PTR, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]

        def _wndproc(hWnd, msg, wParam, lParam):
            if msg in (WM_WINDOWPOSCHANGING, WM_WINDOWPOSCHANGED, WM_ACTIVATE, WM_ACTIVATEAPP):
                QtCore.QTimer.singleShot(0, self._ensure_topmost)
            return user32.CallWindowProcW(self._old_wndproc, hWnd, msg, wParam, lParam)

        self._wndproc_cb = WndProcType(_wndproc)
        proc_ptr = LONG_PTR(ctypes.cast(self._wndproc_cb, ctypes.c_void_p).value)
        previous = user32.SetWindowLongPtrW(hwnd, GWLP_WNDPROC, proc_ptr)
        if not previous:
            self._wndproc_cb = None
            return
        self._old_wndproc = previous

    def _remove_wndproc_hook(self) -> None:
        if sys.platform != "win32" or not self._old_wndproc:
            return
        hwnd = int(self.winId())
        if not hwnd:
            return
        user32 = ctypes.windll.user32
        user32.SetWindowLongPtrW.restype = LONG_PTR
        user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, LONG_PTR]
        user32.SetWindowLongPtrW(hwnd, GWLP_WNDPROC, self._old_wndproc)
        self._old_wndproc = None
        self._wndproc_cb = None

    def _register_shell_hook(self) -> None:
        if sys.platform != "win32" or self._shell_hook_registered:
            return
        hwnd = int(self.winId())
        if not hwnd:
            return
        user32 = ctypes.windll.user32
        if user32.RegisterShellHookWindow(hwnd):
            self._shell_hook_registered = True

    def _unregister_shell_hook(self) -> None:
        if sys.platform != "win32" or not self._shell_hook_registered:
            return
        hwnd = int(self.winId())
        if not hwnd:
            return
        user32 = ctypes.windll.user32
        user32.DeregisterShellHookWindow(hwnd)
        self._shell_hook_registered = False

    def _apply_palette(self) -> None:
        for label in self.label_widgets:
            label.setStyleSheet(
                f"color: {self.text_color.name(QtGui.QColor.NameFormat.HexRgb)};"
                f" background-color: {self._rgba_background()}; padding: 2px 4px;"
            )

    def _rgba_background(self) -> str:
        color = QtGui.QColor(self.background_color)
        color.setAlpha(self.background_opacity)
        return color.name(QtGui.QColor.NameFormat.HexArgb)

    def _update_filter_label(self) -> None:
        if self.search_buffer:
            self.filter_label.setText(f"🔍 {self.search_buffer}")
            self.filter_label.show()
            self._update_filter_label_position()
        else:
            self.filter_label.hide()

    def _update_filter_label_position(self) -> None:
        if not self.search_buffer:
            return
        self.filter_label.adjustSize()
        label_width = self.filter_label.width()
        label_height = self.filter_label.height()
        x = self.width() - label_width - 4
        y = 4
        self.filter_label.move(x, y)
