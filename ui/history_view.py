import os
import subprocess
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QFrame, QMessageBox, QLineEdit
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from core.i18n import t
from ui.theme import *

class HistoryView(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._init_ui()

    def _init_ui(self):
        l = QVBoxLayout(self)
        l.setContentsMargins(40, 40, 40, 40)
        
        top = QHBoxLayout()
        self.lbl_h = QLabel(t("history"))
        self.lbl_h.setFont(QFont(FONT_FAMILY, 16, QFont.Weight.Bold))
        self.lbl_h.setStyleSheet(f"color: {TEXT_COLOR};")
        top.addWidget(self.lbl_h)
        
        top.addSpacing(20)
        self.in_search = QLineEdit()
        self.in_search.setPlaceholderText("Kütüphanede ara...")
        self.in_search.setStyleSheet(f"background-color: {PANEL_COLOR}; color: {TEXT_COLOR}; border: 1px solid {BORDER_COLOR}; border-radius: 6px; padding: 6px; max-width: 200px;")
        self.in_search.textChanged.connect(self.refresh_history)
        top.addWidget(self.in_search)
        
        self.btn_clear_h = QPushButton(f"🗑️ {t('clear_history')}")
        self.btn_clear_h.clicked.connect(self._clear_history)
        self.btn_clear_h.setStyleSheet(f"background-color: {ACCENT_RED}; color: white; font-weight: bold; border-radius: 6px; padding: 8px 16px;")
        top.addStretch()
        top.addWidget(self.btn_clear_h)
        
        self.btn_ref_h = QPushButton(f"🔄 {t('refresh')}")
        self.btn_ref_h.clicked.connect(self.refresh_history)
        self.btn_ref_h.setStyleSheet(f"background-color: {ACCENT_BLUE}; color: white; font-weight: bold; border-radius: 6px; padding: 8px 16px;")
        top.addWidget(self.btn_ref_h)
        l.addLayout(top)
        
        self.scroll_h = QScrollArea()
        self.scroll_h.setWidgetResizable(True)
        self.scroll_h.setStyleSheet("border: none; background: transparent;")
        self.hist_c = QWidget()
        self.hist_c.setStyleSheet("background: transparent;")
        self.hist_l = QVBoxLayout(self.hist_c)
        self.hist_l.setAlignment(Qt.AlignTop)
        self.scroll_h.setWidget(self.hist_c)
        l.addWidget(self.scroll_h)

    def retranslate_ui(self):
        self.lbl_h.setText(t("history"))
        self.btn_clear_h.setText(f"🗑️ {t('clear_history')}")
        self.btn_ref_h.setText(f"🔄 {t('refresh')}")
        self.refresh_history()

    def _clear_history(self):
        reply = QMessageBox.question(self, t("clear_history"), "Emin misiniz?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.main_window.db.clear_history()
            self.refresh_history()
            self.main_window.refresh_dashboard_stats()

    def refresh_history(self):
        while self.hist_l.count(): 
            w = self.hist_l.takeAt(0).widget()
            w.deleteLater() if w else None
            
        history = self.main_window.db.get_history()
        query = self.in_search.text().lower().strip()
        
        for h in history:
            url, title, file_path, status, timestamp = h
            if query and query not in title.lower() and query not in url.lower():
                continue
            c = QFrame()
            c.setStyleSheet(f"QFrame {{ background-color: {PANEL_COLOR}; border: 1px solid {BORDER_COLOR}; border-radius: {BORDER_RADIUS}; padding: 12px; }}")
            hl = QHBoxLayout(c)
            title_lbl = QLabel(f"[{timestamp[:16]}] {title} ({status})")
            title_lbl.setStyleSheet(f"color: {TEXT_COLOR}; border: none; font-size: 14px;")
            hl.addWidget(title_lbl)
            hl.addStretch()
            if status == "completed":
                b = QPushButton(t("open_file"))
                b.setStyleSheet(f"background-color: {ACCENT_GREEN}; color: #11111b; border-radius: 6px; font-weight: bold; padding: 6px 12px; border: none;")
                b.clicked.connect(lambda checked=False, p=file_path: subprocess.run(['explorer', '/select,', os.path.normpath(p)]))
                hl.addWidget(b)
            self.hist_l.addWidget(c)
