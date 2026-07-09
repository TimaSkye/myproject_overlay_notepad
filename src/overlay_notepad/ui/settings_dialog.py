import math
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from ..settings import (
    AppSettings,
    DEFAULT_BACKGROUND_COLOR,
    DEFAULT_FONT_FAMILY,
    DEFAULT_FONT_PT,
    DEFAULT_OPACITY,
    DEFAULT_ROW_HEIGHT,
    DEFAULT_TEXT_COLOR,
)
from .area_selector import AreaSelectorDialog


class AreaHighlightOverlay(QtWidgets.QWidget):
    """Полупрозрачная рамка поверх выбранной области."""

    def __init__(self) -> None:
        """Создаёт подсветку выбранной области."""
        flags = (
            QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.Tool
            | QtCore.Qt.WindowType.WindowStaysOnTopHint
        )
        super().__init__(None, flags)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.hide()
        self._pulse_phase = 0.0
        self._pulse_timer = QtCore.QTimer(self)
        self._pulse_timer.setInterval(40)
        self._pulse_timer.timeout.connect(self._advance_pulse)

    def update_region(self, rect: QtCore.QRect | None) -> None:
        """Показывает подсветку для указанного прямоугольника."""
        if rect and rect.isValid():
            margin = 2
            geo = rect.adjusted(-margin, -margin, margin, margin)
            self.setGeometry(geo)
            self.raise_()
            self.show()
            self.update()
            if not self._pulse_timer.isActive():
                self._pulse_timer.start()
        else:
            self.hide()
            self._pulse_timer.stop()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # noqa: N802
        """Рисует рамку и свечение вокруг зоны."""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QtGui.QColor(0, 0, 0, 0))

        base_pen = QtGui.QPen(QtGui.QColor(26, 115, 232), 2)
        painter.setPen(base_pen)
        painter.drawRect(self.rect().adjusted(1, 1, -2, -2))

        glow_strength = (math.sin(self._pulse_phase) + 1) / 2
        glow_alpha = 60 + int(glow_strength * 80)
        glow_pen = QtGui.QPen(QtGui.QColor(26, 115, 232, glow_alpha), 6)
        glow_pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
        painter.setPen(glow_pen)
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

    def _advance_pulse(self) -> None:
        """Обновляет фазу пульсации подсветки."""
        if not self.isVisible():
            return
        self._pulse_phase = (self._pulse_phase + 0.12) % (2 * math.pi)
        self.update()


class SettingsDialog(QtWidgets.QDialog):
    """Позволяет выбрать файл данных и задать позицию окна."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        """Инициализирует диалог с элементами управления настройками."""
        super().__init__(parent)
        self.setWindowTitle("Настройки Overlay Notepad")
        self.setModal(True)
        self.setFixedSize(480, 480)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            """
            QDialog {
                background-color: #f6f8fb;
                color: #202124;
                font-family: 'Google Sans', 'Segoe UI', Arial, sans-serif;
            }
            #settingsCard {
                background-color: #ffffff;
                border-radius: 18px;
                border: 1px solid rgba(60, 64, 67, 0.08);
                padding: 18px 22px;
            }
            QLabel.sectionTitle {
                font-size: 12px;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                color: #5f6368;
            }
            QLineEdit, QSpinBox, QFontComboBox {
                background-color: #fbfcff;
                border: 1px solid rgba(60, 64, 67, 0.16);
                border-radius: 8px;
                padding: 6px 12px;
            }
            QPushButton {
                border-radius: 999px;
                padding: 9px 20px;
                font-weight: 600;
                letter-spacing: 0.04em;
                text-transform: uppercase;
                transition: background-color 120ms ease, border-color 120ms ease;
            }
            QPushButton:pressed {
                transform: translateY(1px);
            }
            QPushButton.primaryButton {
                background-color: #1a73e8;
                color: #ffffff;
                border: none;
            }
            QPushButton.primaryButton:hover {
                background-color: #185abc;
            }
            QPushButton.primaryButton:pressed {
                background-color: #0f5adb;
            }
            QPushButton.secondaryButton {
                background-color: #e8f0fe;
                color: #1a73e8;
                border: none;
            }
            QPushButton.secondaryButton:hover {
                background-color: #d2e3fc;
            }
            QPushButton.secondaryButton:pressed {
                background-color: #c6dafc;
            }
            QPushButton#outlineButton {
                background-color: #ffffff;
                color: #1a73e8;
                border: 1px solid rgba(26, 115, 232, 0.8);
            }
            QPushButton#outlineButton:hover {
                background-color: #eef3ff;
            }
            QPushButton#outlineButton:pressed {
                background-color: #e3ebff;
            }
            """
        )

        header_layout = QtWidgets.QVBoxLayout()
        title_label = QtWidgets.QLabel("Overlay Notepad")
        title_label.setStyleSheet("font-size: 20px; font-weight: 600; color: #202124;")
        subtitle_label = QtWidgets.QLabel("Настройте внешний вид оверлея")
        subtitle_label.setStyleSheet("color: #64748b; margin-bottom: 12px;")
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)

        self.file_edit = QtWidgets.QLineEdit()
        browse_button = QtWidgets.QPushButton("Обзор…")
        browse_button.setProperty("class", "secondaryButton")
        browse_button.clicked.connect(self._browse_file)

        file_layout = QtWidgets.QHBoxLayout()
        file_layout.addWidget(self.file_edit)
        file_layout.addWidget(browse_button)

        self.area_button = QtWidgets.QPushButton("Выбрать область отображения")
        self.area_button.setObjectName("outlineButton")
        self.area_button.clicked.connect(self._select_area)

        area_layout = QtWidgets.QHBoxLayout()
        area_layout.addWidget(self.area_button)

        self.row_height_spin = QtWidgets.QSpinBox()
        self.row_height_spin.setRange(10, 200)
        self.row_height_spin.setValue(DEFAULT_ROW_HEIGHT)
        self.row_height_spin.setSuffix(" px")

        self.font_spin = QtWidgets.QSpinBox()
        self.font_spin.setRange(5, 72)
        self.font_spin.setValue(DEFAULT_FONT_PT)
        self.font_spin.setSuffix(" pt")

        self.font_combo = QtWidgets.QFontComboBox()
        self.font_combo.setCurrentFont(QtGui.QFont(DEFAULT_FONT_FAMILY))

        self.opacity_spin = QtWidgets.QSpinBox()
        self.opacity_spin.setRange(30, 255)
        self.opacity_spin.setValue(DEFAULT_OPACITY)
        self.opacity_spin.setSuffix(" (α)")

        self.auto_launch_checkbox = QtWidgets.QCheckBox("Автозапуск при старте Windows")
        self.auto_launch_checkbox.setToolTip("Добавить Overlay Notepad в автозагрузку текущего пользователя")

        self.bg_color_btn = self._create_color_button(DEFAULT_BACKGROUND_COLOR)
        self.bg_color_btn.clicked.connect(lambda: self._pick_color("background"))
        self.text_color_btn = self._create_color_button(DEFAULT_TEXT_COLOR)
        self.text_color_btn.clicked.connect(lambda: self._pick_color("text"))

        form_layout = QtWidgets.QFormLayout()
        form_layout.addRow("Файл с данными:", file_layout)
        form_layout.addRow("Область:", area_layout)
        form_layout.addRow("Высота строки:", self.row_height_spin)
        form_layout.addRow("Размер шрифта:", self.font_spin)
        form_layout.addRow("Семейство шрифта:", self.font_combo)
        form_layout.addRow("Прозрачность (0-255):", self.opacity_spin)

        palette_layout = QtWidgets.QHBoxLayout()
        palette_layout.addWidget(QtWidgets.QLabel("Фон:"))
        palette_layout.addWidget(self.bg_color_btn)
        palette_layout.addSpacing(12)
        palette_layout.addWidget(QtWidgets.QLabel("Текст:"))
        palette_layout.addWidget(self.text_color_btn)
        form_layout.addRow("Палитра:", palette_layout)
        form_layout.addRow(" ", self.auto_launch_checkbox)

        buttons = QtWidgets.QDialogButtonBox()
        ok_button = buttons.addButton("Сохранить", QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole)
        cancel_button = buttons.addButton("Отмена", QtWidgets.QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        card_frame = QtWidgets.QFrame()
        card_frame.setObjectName("settingsCard")
        card_layout = QtWidgets.QVBoxLayout(card_frame)
        section_label = QtWidgets.QLabel("Параметры отображения")
        section_label.setProperty("class", "sectionTitle")
        card_layout.addWidget(section_label)
        card_layout.addSpacing(4)
        card_layout.addLayout(form_layout)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addLayout(header_layout)
        main_layout.addWidget(card_frame)
        main_layout.addStretch(1)
        ok_button.setProperty("class", "primaryButton")
        cancel_button.setProperty("class", "secondaryButton")
        main_layout.addWidget(buttons, alignment=QtCore.Qt.AlignmentFlag.AlignRight)

        self._position = QtCore.QPoint(0, 0)
        self._size = QtCore.QSize(320, 64)
        self._area_rect = QtCore.QRect()
        self._area_confirmed = False
        self._background_color = QtGui.QColor(DEFAULT_BACKGROUND_COLOR)
        self._text_color = QtGui.QColor(DEFAULT_TEXT_COLOR)
        self._area_overlay = AreaHighlightOverlay()
        self.destroyed.connect(self._area_overlay.deleteLater)

    def set_values(self, settings: AppSettings) -> None:
        """Заполняет элементы управления значениями настроек."""
        self.file_edit.setText(str(settings.file_path))
        self._position = settings.position
        self._size = settings.size
        self._area_rect = QtCore.QRect(self._position, self._size)
        self._area_confirmed = self._area_rect.isValid()
        self.row_height_spin.setValue(settings.row_height)
        self.font_spin.setValue(settings.font_pt)
        self.font_combo.setCurrentFont(QtGui.QFont(settings.font_family))
        self.opacity_spin.setValue(settings.background_opacity)
        self._background_color = QtGui.QColor(settings.background_color)
        self._text_color = QtGui.QColor(settings.text_color)
        self._update_color_button(self.bg_color_btn, self._background_color)
        self._update_color_button(self.text_color_btn, self._text_color)
        self.auto_launch_checkbox.setChecked(settings.auto_launch)
        self._update_area_overlay()

    def get_settings(self) -> AppSettings:
        """Собирает текущее состояние UI в объект AppSettings."""
        return AppSettings(
            file_path=Path(self.file_edit.text()).expanduser(),
            position=self._position,
            size=self._size,
            row_height=self.row_height_spin.value(),
            font_pt=self.font_spin.value(),
            font_family=self.font_combo.currentFont().family(),
            background_opacity=self.opacity_spin.value(),
            background_color=self._background_color.name(QtGui.QColor.NameFormat.HexRgb),
            text_color=self._text_color.name(QtGui.QColor.NameFormat.HexRgb),
            auto_launch=self.auto_launch_checkbox.isChecked(),
        )

    def showEvent(self, event: QtGui.QShowEvent) -> None:  # noqa: N802
        super().showEvent(event)
        self._update_area_overlay()

    def hideEvent(self, event: QtGui.QHideEvent) -> None:  # noqa: N802
        self._area_overlay.update_region(None)
        super().hideEvent(event)

    def _browse_file(self) -> None:
        """Открывает диалог выбора файла данных."""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Выберите файл", self.file_edit.text() or "file.txt")
        if path:
            self.file_edit.setText(path)

    def _select_area(self) -> None:
        """Запускает выбор области для отображения оверлея."""
        initial_rect = QtCore.QRect(self._position, self._size)
        self._area_overlay.update_region(None)
        result = AreaSelectorDialog.pick_area(self, initial_rect if initial_rect.isValid() else None)
        if result is None:
            self._update_area_overlay()
            return
        position, size = result
        self._position = position
        self._size = size
        self._area_rect = QtCore.QRect(position, size)
        self._area_confirmed = True
        self._update_area_overlay()

    def _update_area_overlay(self) -> None:
        """Отрисовывает подсветку текущей выделенной области."""
        rect = QtCore.QRect(self._position, self._size)
        if not self.isVisible():
            self._area_overlay.update_region(None)
            return
        if self._area_confirmed and rect.isValid():
            self._area_overlay.update_region(rect)
        else:
            self._area_overlay.update_region(None)

    def _create_color_button(self, color_hex: str) -> QtWidgets.QPushButton:
        """Создаёт кнопку с отображением цвета."""
        button = QtWidgets.QPushButton()
        button.setFixedSize(46, 24)
        self._update_color_button(button, QtGui.QColor(color_hex))
        return button


    def _update_color_button(self, button: QtWidgets.QPushButton, color: QtGui.QColor) -> None:
        """Меняет стиль кнопки под выбранный цвет."""
        button.setStyleSheet(
            f"background-color: {color.name(QtGui.QColor.NameFormat.HexRgb)}; border: 1px solid #555;"
        )

    def _pick_color(self, target: str) -> None:
        """Показывает диалог выбора цвета и сохраняет результат."""
        initial = self._background_color if target == "background" else self._text_color
        color = QtWidgets.QColorDialog.getColor(initial, self, "Выберите цвет")
        if not color.isValid():
            return
        if target == "background":
            self._background_color = color
            self._update_color_button(self.bg_color_btn, color)
        else:
            self._text_color = color
            self._update_color_button(self.text_color_btn, color)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # noqa: N802
        self._area_overlay.update_region(None)
        self._area_overlay.close()
        super().closeEvent(event)


