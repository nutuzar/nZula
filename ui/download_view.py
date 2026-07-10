import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from core.i18n import t
from ui.theme import *

class DownloadView(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._init_ui()

    def _init_ui(self):
        l = QVBoxLayout(self)
        l.setContentsMargins(40, 40, 40, 40)
        
        top = QHBoxLayout()
        self.lbl_dl = QLabel(t("download_queue"))
        self.lbl_dl.setFont(QFont(FONT_FAMILY, 16, QFont.Weight.Bold))
        self.lbl_dl.setStyleSheet(f"color: {TEXT_COLOR};")
        top.addWidget(self.lbl_dl)
        
        self.btn_clear_q = QPushButton(f"🧹 {t('clear_list')}")
        self.btn_clear_q.setStyleSheet(f"background-color: {ACCENT_RED}; color: white; font-weight: bold; border-radius: 6px; padding: 8px 16px;")
        self.btn_clear_q.clicked.connect(self._clear_queue)
        
        self.btn_start_q = QPushButton(f"▶️ {t('start_queue')}")
        self.btn_start_q.setStyleSheet(f"background-color: {ACCENT_GREEN}; color: #11111b; font-weight: bold; border-radius: 6px; padding: 8px 16px;")
        self.btn_start_q.clicked.connect(self.main_window._start_queue)
        
        top.addStretch()
        top.addWidget(self.btn_clear_q)
        top.addWidget(self.btn_start_q)
        l.addLayout(top)
        
        self.scroll_d = QScrollArea()
        self.scroll_d.setWidgetResizable(True)
        self.scroll_d.setStyleSheet("border: none; background: transparent;")
        self.dl_c = QWidget()
        self.dl_c.setStyleSheet("background: transparent;")
        self.dl_l = QVBoxLayout(self.dl_c)
        self.dl_l.setAlignment(Qt.AlignTop)
        self.scroll_d.setWidget(self.dl_c)
        l.addWidget(self.scroll_d)

    def retranslate_ui(self):
        self.lbl_dl.setText(t("download_queue"))
        self.btn_clear_q.setText(f"🧹 {t('clear_list')}")
        self.btn_start_q.setText(f"▶️ {t('start_queue')}")

    def add_widget(self, widget):
        self.dl_l.addWidget(widget)

    def _clear_queue(self):
        to_delete = []
        for key, w in self.main_window.download_widgets.items():
            if w.is_finished:
                to_delete.append(key)
                w.deleteLater()
            elif key not in self.main_window.download_workers or not self.main_window.download_workers[key].isRunning():
                to_delete.append(key)
                w.deleteLater()
                if key in self.main_window.download_workers:
                    self.main_window.download_workers[key].cancel()
        
        for key in to_delete:
            if key in self.main_window.download_widgets: del self.main_window.download_widgets[key]
            if key in self.main_window.download_workers: del self.main_window.download_workers[key]
