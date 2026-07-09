from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets


ASSETS_ROOT = Path(__file__).resolve().parent.parent.parent
GITHUB_ICON_PATH = ASSETS_ROOT / "github.png"
TELEGRAM_ICON_PATH = ASSETS_ROOT / "telegram.png"


class AboutDialog(QtWidgets.QDialog):
    """Диалог с информацией о приложении, данных и разработчике."""

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
        *,
        image_path: Path | None = None,
        donation_qr_path: Path | None = None,
        app_icon: QtGui.QIcon | None = None,
    ) -> None:
        """Создаёт окно «О программе» с опциональными ресурсами."""
        super().__init__(parent)
        self.setWindowTitle("О программе")
        self.setModal(True)
        self.setMinimumWidth(480)
        self._account_number = "40817810672002253974"
        self._donation_qr_path = donation_qr_path
        if app_icon and not app_icon.isNull():
            self.setWindowIcon(app_icon)
        self._build_ui(image_path)

    def _build_ui(self, image_path: Path | None) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(16)

        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setSpacing(12)
        layout.addLayout(header_layout)

        icon_label = QtWidgets.QLabel()
        icon_label.setFixedSize(84, 84)
        pixmap = self._load_pixmap(image_path)
        if not pixmap.isNull():
            icon_label.setPixmap(
                pixmap.scaled(
                    icon_label.size(),
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                    QtCore.Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            icon_label.setVisible(False)
        header_layout.addWidget(icon_label)

        description_label = QtWidgets.QLabel(
            "<b>Overlay Notepad</b><br>"
            "Простая и бесплатная утилита-оверлей, которая всегда остаётся поверх окон, "
            "показывает пары «ключ – значение» из выбранного файла и позволяет копировать "
            "значения одним кликом."
        )
        description_label.setWordWrap(True)
        description_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        header_layout.addWidget(description_label, 1)

        format_group = QtWidgets.QGroupBox("Формат данных file.txt")
        format_layout = QtWidgets.QVBoxLayout(format_group)
        format_text = QtWidgets.QLabel(
            "<p>Каждая строка <code>file.txt</code> — отдельный JSON-объект с одной парой "
            "ключ–значение. Файл читается в кодировке UTF-8 без BOM, пустые строки "
            "пропускаются.</p>"
            "<ul>"
            "<li>ключ используется для поиска и отображается слева;</li>"
            "<li>значение копируется в буфер обмена при клике;</li>"
            "<li>дополнительные поля игнорируются.</li>"
            "</ul>"
            "<p>Пример строки:</p>"
            "<pre>{&quot;VPN пароль&quot;: &quot;SeCr3t!&quot;}</pre>"
            "<p>Можно хранить сколько угодно строк: приложение подхватит изменения "
            "автоматически при сохранении файла.</p>"
        )
        format_text.setTextFormat(QtCore.Qt.TextFormat.RichText)
        format_text.setWordWrap(True)
        format_layout.addWidget(format_text)
        layout.addWidget(format_group)

        tips_group = QtWidgets.QGroupBox("Подсказки по работе")
        tips_layout = QtWidgets.QVBoxLayout(tips_group)
        tips_label = QtWidgets.QLabel(
            "<ul>"
            "<li>Кликните ЛКМ по строке, чтобы скопировать значение в буфер обмена.</li>"
            "<li>Используйте колесо мыши для прокрутки списка заметок.</li>"
            "<li>Начните печатать при наведении курсора, чтобы отфильтровать записи.</li>"
            "<li>ПКМ по виджету откроет контекстное меню с настройками и выбором файла.</li>"
            "</ul>"
        )
        tips_label.setWordWrap(True)
        tips_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        tips_layout.addWidget(tips_label)
        layout.addWidget(tips_group)

        developer_group = QtWidgets.QGroupBox("О разработчике")
        developer_layout = QtWidgets.QVBoxLayout(developer_group)
        developer_label = QtWidgets.QLabel(
            '<b>Тимур "Skye" Даянов</b><br>'
            "Python-разработчик и автор небольших side-проектов. В свободное от основной "
            "работы время экспериментирует с оверлеями, осваивает новые подходы к UX и "
            "делится своими находками с теми, кому нужны быстрые инструменты под рукой. "
            "Overlay Notepad вырос из личной привычки хранить подсказки рядом, а теперь "
            "превращается в набор мини-приложений для людей, которые ценят скорость и "
            "простоту."
        )
        developer_label.setWordWrap(True)
        developer_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        developer_layout.addWidget(developer_label)

        links_and_button = QtWidgets.QWidget()
        links_layout = QtWidgets.QHBoxLayout(links_and_button)
        links_layout.setContentsMargins(0, 0, 0, 0)
        links_layout.setSpacing(12)

        links_column = QtWidgets.QVBoxLayout()
        links_column.setContentsMargins(0, 0, 0, 0)
        links_column.setSpacing(6)
        links_column.addWidget(
            self._create_contact_link(
                icon_path=GITHUB_ICON_PATH,
                text="GitHub — TimaSkye",
                url="https://github.com/TimaSkye",
            )
        )
        links_column.addWidget(
            self._create_contact_link(
                icon_path=TELEGRAM_ICON_PATH,
                text="Telegram — @tima_skye",
                url="https://t.me/tima_skye",
            )
        )
        links_layout.addLayout(links_column, 1)

        donate_button = QtWidgets.QPushButton("Поддержать автора")
        donate_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        donate_button.setStyleSheet(
            "font-weight:600; padding:6px 16px; background-color:#1f8aee; color:white;"
        )
        donate_button.clicked.connect(self._open_donation_window)
        links_layout.addWidget(donate_button, alignment=QtCore.Qt.AlignmentFlag.AlignRight)

        developer_layout.addWidget(links_and_button)
        layout.addWidget(developer_group)

        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box, alignment=QtCore.Qt.AlignmentFlag.AlignRight)

    @staticmethod
    def _load_pixmap(path: Path | None) -> QtGui.QPixmap:
        pixmap = QtGui.QPixmap()
        if path and path.exists():
            pixmap = QtGui.QPixmap(str(path))
        return pixmap

    def _open_donation_window(self) -> None:
        dialog = DonationDialog(
            self,
            account_number=self._account_number,
            donation_qr_path=self._donation_qr_path,
        )
        dialog.exec()

    def _create_contact_link(self, *, icon_path: Path | None, text: str, url: str) -> QtWidgets.QWidget:
        container = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        icon_label = QtWidgets.QLabel()
        icon_label.setFixedSize(20, 20)
        pixmap = self._load_pixmap(icon_path)
        if not pixmap.isNull():
            icon_label.setPixmap(
                pixmap.scaled(
                    icon_label.size(),
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                    QtCore.Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            icon_label.setText("•")
            icon_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        link_label = QtWidgets.QLabel(f'<a href="{url}">{text}</a>')
        link_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        link_label.setOpenExternalLinks(True)
        link_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        link_label.setStyleSheet("font-weight:600; color:#1d63ff;")
        layout.addWidget(link_label, 1)
        layout.addStretch()
        return container


class DonationDialog(QtWidgets.QDialog):
    """Отдельное окно с реквизитами и QR-кодом."""

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
        *,
        account_number: str,
        donation_qr_path: Path | None = None,
    ) -> None:
        """Показывает платёжные реквизиты и QR-код."""
        super().__init__(parent)
        self.setWindowTitle("Поддержать автора")
        self.setModal(True)
        self.setMinimumWidth(420)
        self._account_number = account_number
        self._donation_qr_path = donation_qr_path
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(16)

        message_label = QtWidgets.QLabel(
            "<h3>Спасибо, что вдохновляете проект!</h3>"
            "<p>Overlay Notepad родился как личная необходимость и превратился в маленького помощника для тех, кто живёт в задачах и заметках.</p>"
        )
        message_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        message_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        message_label.setWordWrap(True)
        layout.addWidget(message_label)

        vision_label = QtWidgets.QLabel(
            "<p>Любая поддержка помогает мне освободить немного времени для создания новых проектов, "
            "помогает заводить прототипы, улучшать гайды по продуктивности и делиться свежими "
            "релизами. Вы вкладываетесь не только в Overlay Notepad, но и в будущее "
            "небольших, но очень полезных инструментов.</p>"
        )
        vision_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        vision_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        vision_label.setWordWrap(True)
        layout.addWidget(vision_label)

        account_label = QtWidgets.QLabel(
            "Номер счёта Сбербанк:<br>"
            f"<b>{self._spaced_account_number()}</b>"
        )
        account_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        account_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        account_label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(account_label)

        copy_button = QtWidgets.QPushButton("Скопировать номер")
        copy_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        copy_button.clicked.connect(self._copy_account_to_clipboard)
        layout.addWidget(copy_button, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

        qr_pixmap = self._load_pixmap(self._donation_qr_path)
        if not qr_pixmap.isNull():
            qr_label = QtWidgets.QLabel()
            qr_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            qr_label.setPixmap(
                qr_pixmap.scaled(
                    220,
                    220,
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                    QtCore.Qt.TransformationMode.SmoothTransformation,
                )
            )
            layout.addWidget(qr_label)

        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

    def _copy_account_to_clipboard(self) -> None:
        QtGui.QGuiApplication.clipboard().setText(self._account_number)
        QtWidgets.QToolTip.showText(
            self.mapToGlobal(self.rect().center()),
            "Номер счёта скопирован",
            self,
            self.rect(),
            1500,
        )

    def _spaced_account_number(self) -> str:
        groups = [self._account_number[i : i + 4] for i in range(0, len(self._account_number), 4)]
        return " ".join(groups)

    @staticmethod
    def _load_pixmap(path: Path | None) -> QtGui.QPixmap:
        pixmap = QtGui.QPixmap()
        if path and path.exists():
            pixmap = QtGui.QPixmap(str(path))
        return pixmap
