from PySide6 import QtCore, QtGui, QtWidgets


class AreaSelectorDialog(QtWidgets.QDialog):
    """Полноэкранный оверлей для выбора прямоугольника."""

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
        initial_rect: QtCore.QRect | None = None,
    ) -> None:
        """Готовит полноэкранный слой для выбора прямоугольника."""
        flags = (
            QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.Tool
            | QtCore.Qt.WindowType.WindowStaysOnTopHint
        )
        super().__init__(parent, flags)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
        self.setCursor(QtCore.Qt.CursorShape.CrossCursor)
        self._origin = QtCore.QPoint()
        self._current = QtCore.QPoint()
        self._dragging = False
        self._selection = QtCore.QRect()
        self._initial_rect = QtCore.QRect(initial_rect) if initial_rect else None
        self._init_geometry()
        self._apply_initial_selection()

    def _init_geometry(self) -> None:
        rect = QtCore.QRect()
        for screen in QtGui.QGuiApplication.screens():
            rect = rect.united(screen.geometry()) if rect.isValid() else screen.geometry()
        if not rect.isValid():
            rect = QtGui.QGuiApplication.primaryScreen().geometry()
        self.setGeometry(rect)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._dragging = True
            self._origin = event.position().toPoint()
            self._current = self._origin
            self._selection = QtCore.QRect(self._origin, self._current)
            self.update()
        elif event.button() == QtCore.Qt.MouseButton.RightButton:
            self.reject()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        if self._dragging:
            self._current = event.position().toPoint()
            self._selection = QtCore.QRect(self._origin, self._current).normalized()
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        if self._dragging and event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._dragging = False
            self._current = event.position().toPoint()
            self._selection = QtCore.QRect(self._origin, self._current).normalized()
            if self._selection.width() >= 50 and self._selection.height() >= 30:
                self.accept()
            else:
                self._selection = QtCore.QRect()
                self.update()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:  # noqa: N802
        if event.key() == QtCore.Qt.Key.Key_Escape:
            self.reject()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # noqa: N802
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        overlay_color = QtGui.QColor(0, 0, 0, 120)
        painter.fillRect(self.rect(), overlay_color)

        rect_to_draw = self._selection if self._selection.isValid() else self._initial_rect
        if rect_to_draw and rect_to_draw.isValid():
            painter.setCompositionMode(QtGui.QPainter.CompositionMode_Clear)
            painter.fillRect(rect_to_draw, QtGui.QColor(0, 0, 0, 0))
            painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceOver)
            pen = QtGui.QPen(QtGui.QColor(91, 155, 213), 2)
            painter.setPen(pen)
            painter.drawRect(rect_to_draw)

        painter.setPen(QtGui.QPen(QtGui.QColor("white")))
        painter.setFont(QtGui.QFont("Segoe UI", 11))
        painter.drawText(
            20,
            40,
            "Выделите область левой кнопкой. Правая кнопка или ESC — отмена.",
        )

    def _apply_initial_selection(self) -> None:
        if self._initial_rect and self._initial_rect.isValid():
            self._selection = self._initial_rect
            self.update()

    @classmethod
    def pick_area(
        cls,
        parent: QtWidgets.QWidget | None = None,
        initial_rect: QtCore.QRect | None = None,
    ) -> tuple[QtCore.QPoint, QtCore.QSize] | None:
        dialog = cls(parent, initial_rect)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted and dialog._selection.isValid():
            rect = dialog._selection
            return rect.topLeft(), rect.size()
        return None
