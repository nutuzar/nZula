from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from core.i18n import t
from ui.theme import *

class AboutView(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._init_ui()

    def _init_ui(self):
        l = QVBoxLayout(self)
        l.setContentsMargins(50, 50, 50, 50)
        l.setAlignment(Qt.AlignCenter)
        
        title = QLabel("nZula")
        title.setFont(QFont(FONT_FAMILY, 36, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ACCENT_BLUE};")
        title.setAlignment(Qt.AlignCenter)
        l.addWidget(title)
        
        self.lbl_vers = QLabel(t("version"))
        self.lbl_vers.setStyleSheet(f"color: {SUBTEXT_COLOR}; font-size: 16px;")
        self.lbl_vers.setAlignment(Qt.AlignCenter)
        l.addWidget(self.lbl_vers)
        
        self.lbl_dev = QLabel(f"{t('developer')} nutuzar")
        self.lbl_dev.setStyleSheet(f"color: {ACCENT_GREEN}; font-size: 18px; margin-top: 20px;")
        self.lbl_dev.setAlignment(Qt.AlignCenter)
        l.addWidget(self.lbl_dev)
        
        l.addStretch()

    def retranslate_ui(self):
        self.lbl_vers.setText(t("version"))
        self.lbl_dev.setText(f"{t('developer')} nutuzar")
