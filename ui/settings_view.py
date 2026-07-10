import sys
import subprocess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, 
    QCheckBox, QComboBox, QLineEdit, QGridLayout, QFileDialog, QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from core.i18n import t
from ui.theme import *

class SettingsView(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._init_ui()

    def _init_ui(self):
        main_l = QVBoxLayout(self)
        main_l.setContentsMargins(0, 0, 0, 0)
        
        self.set_scroll = QScrollArea()
        self.set_scroll.setWidgetResizable(True)
        self.set_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        set_w = QWidget()
        set_w.setStyleSheet("background: transparent;")
        l = QVBoxLayout(set_w)
        l.setContentsMargins(40, 40, 40, 40)
        l.setSpacing(20)
        
        self.lbl_set = QLabel(t("settings"))
        self.lbl_set.setFont(QFont(FONT_FAMILY, 16, QFont.Weight.Bold))
        self.lbl_set.setStyleSheet(f"color: {TEXT_COLOR};")
        l.addWidget(self.lbl_set)
        
        form = QGridLayout()
        form.setSpacing(15)
        
        self.sp_limit = QComboBox()
        self.sp_limit.addItems(["1", "2", "3", "4", "5", "10"])
        self.sp_limit.setCurrentText(str(self.main_window.config.get("max_concurrent_downloads")))
        self.sp_limit.setStyleSheet(f"background-color: {PANEL_COLOR}; color: {TEXT_COLOR}; border: 1px solid {BORDER_COLOR}; border-radius: 6px; padding: 8px;")
        self.t1 = QLabel(t("max_concurrent"))
        self.t1.setStyleSheet(f"color: {TEXT_COLOR};")
        form.addWidget(self.t1, 0, 0)
        form.addWidget(self.sp_limit, 0, 1)
        
        self.inp_speed = QLineEdit(str(self.main_window.config.get("speed_limit_kbps")))
        self.inp_speed.setStyleSheet(f"background-color: {PANEL_COLOR}; color: {TEXT_COLOR}; border: 1px solid {BORDER_COLOR}; border-radius: 6px; padding: 8px;")
        self.t2 = QLabel(t("speed_limit"))
        self.t2.setStyleSheet(f"color: {TEXT_COLOR};")
        form.addWidget(self.t2, 1, 0)
        form.addWidget(self.inp_speed, 1, 1)
        
        self.chk_shutdown = QCheckBox(t("auto_shutdown"))
        self.chk_shutdown.setChecked(self.main_window.config.get("auto_shutdown"))
        self.chk_shutdown.setStyleSheet(f"color: {TEXT_COLOR};")
        form.addWidget(self.chk_shutdown, 2, 0, 1, 2)
        
        self.inp_tmpl = QLineEdit(self.main_window.config.get("naming_template"))
        self.inp_tmpl.setStyleSheet(f"background-color: {PANEL_COLOR}; color: {TEXT_COLOR}; border: 1px solid {BORDER_COLOR}; border-radius: 6px; padding: 8px;")
        self.t3 = QLabel(t("naming_tmpl"))
        self.t3.setStyleSheet(f"color: {TEXT_COLOR};")
        form.addWidget(self.t3, 3, 0)
        form.addWidget(self.inp_tmpl, 3, 1)
        
        self.chk_sub = QCheckBox(t("subfolder"))
        self.chk_sub.setChecked(self.main_window.config.get("auto_subfolder_by_platform"))
        self.chk_sub.setStyleSheet(f"color: {TEXT_COLOR};")
        form.addWidget(self.chk_sub, 4, 0, 1, 2)
        
        self.chk_nfo = QCheckBox(t("create_nfo"))
        self.chk_nfo.setChecked(self.main_window.config.get("create_nfo"))
        self.chk_nfo.setStyleSheet(f"color: {TEXT_COLOR};")
        form.addWidget(self.chk_nfo, 5, 0, 1, 2)
        
        self.chk_thumb = QCheckBox(t("download_thumb"))
        self.chk_thumb.setChecked(self.main_window.config.get("download_thumbnail"))
        self.chk_thumb.setStyleSheet(f"color: {TEXT_COLOR};")
        form.addWidget(self.chk_thumb, 6, 0, 1, 2)
        
        self.chk_subs = QCheckBox(t("download_subs"))
        self.chk_subs.setChecked(self.main_window.config.get("download_subs"))
        self.chk_subs.setStyleSheet(f"color: {TEXT_COLOR};")
        form.addWidget(self.chk_subs, 7, 0, 1, 2)
        
        self.cb_mp3 = QComboBox()
        self.cb_mp3.addItems(["128", "192", "256", "320"])
        self.cb_mp3.setCurrentText(str(self.main_window.config.get("mp3_quality")))
        self.cb_mp3.setStyleSheet(f"background-color: {PANEL_COLOR}; color: {TEXT_COLOR}; border: 1px solid {BORDER_COLOR}; border-radius: 6px; padding: 8px;")
        self.t_mp3 = QLabel(t("mp3_quality"))
        self.t_mp3.setStyleSheet(f"color: {TEXT_COLOR};")
        form.addWidget(self.t_mp3, 8, 0)
        form.addWidget(self.cb_mp3, 8, 1)

        self.cb_cookies = QComboBox()
        self.cb_cookies.addItems(["Hiçbiri", "Chrome", "Firefox", "Edge", "Opera", "Brave", "Vivaldi", "Safari"])
        curr_cookie = self.main_window.config.get("browser_cookies")
        if curr_cookie:
            idx = self.cb_cookies.findText(curr_cookie.capitalize())
            if idx >= 0: self.cb_cookies.setCurrentIndex(idx)
        self.cb_cookies.setStyleSheet(f"background-color: {PANEL_COLOR}; color: {TEXT_COLOR}; border: 1px solid {BORDER_COLOR}; border-radius: 6px; padding: 8px;")
        self.t_cookie = QLabel("🍪 Çerez (Gizli Videolar)")
        self.t_cookie.setStyleSheet(f"color: {TEXT_COLOR};")
        form.addWidget(self.t_cookie, 9, 0)
        form.addWidget(self.cb_cookies, 9, 1)

        self.inp_proxy = QLineEdit(self.main_window.config.get("proxy"))
        self.inp_proxy.setPlaceholderText("http://user:pass@ip:port")
        self.inp_proxy.setStyleSheet(f"background-color: {PANEL_COLOR}; color: {TEXT_COLOR}; border: 1px solid {BORDER_COLOR}; border-radius: 6px; padding: 8px;")
        self.t4 = QLabel(t("proxy"))
        self.t4.setStyleSheet(f"color: {TEXT_COLOR};")
        form.addWidget(self.t4, 10, 0)
        form.addWidget(self.inp_proxy, 10, 1)
        
        self.in_dir = QLineEdit(str(self.main_window.config.get("download_dir")))
        self.in_dir.setStyleSheet(f"background-color: {PANEL_COLOR}; color: {ACCENT_GREEN}; border: 1px solid {BORDER_COLOR}; border-radius: 6px; padding: 8px;")
        self.btn_dir = QPushButton(t("browse"))
        self.btn_dir.setStyleSheet(f"background-color: {PANEL_COLOR}; color: {TEXT_COLOR}; border-radius: 6px; padding: 8px 16px; border: 1px solid {BORDER_COLOR};")
        self.btn_dir.clicked.connect(self._sel_dir)
        self.t5 = QLabel(t("download_dir"))
        self.t5.setStyleSheet(f"color: {TEXT_COLOR};")
        form.addWidget(self.t5, 11, 0)
        
        dir_l = QHBoxLayout()
        dir_l.addWidget(self.in_dir)
        dir_l.addWidget(self.btn_dir)
        form.addLayout(dir_l, 11, 1)

        l.addLayout(form)
        
        b_row = QHBoxLayout()
        self.btn_save = QPushButton(f"💾 {t('save_settings')}")
        self.btn_save.setStyleSheet(f"background-color: {ACCENT_GREEN}; color: #11111b; font-weight: bold; border-radius: 8px; padding: 12px; font-size: 14px;")
        self.btn_save.clicked.connect(self._save_settings)
        
        self.btn_yup = QPushButton(f"🔄 {t('update_ytdlp')}")
        self.btn_yup.setStyleSheet(f"background-color: {ACCENT_BLUE}; color: white; font-weight: bold; border-radius: 8px; padding: 12px; font-size: 14px;")
        self.btn_yup.clicked.connect(self._update_ytdlp)
        
        b_row.addWidget(self.btn_save)
        b_row.addWidget(self.btn_yup)
        l.addLayout(b_row)
        l.addStretch()
        
        self.set_scroll.setWidget(set_w)
        main_l.addWidget(self.set_scroll)

    def retranslate_ui(self):
        self.lbl_set.setText(t("settings"))
        self.t1.setText(t("max_concurrent"))
        self.t2.setText(t("speed_limit"))
        self.chk_shutdown.setText(t("auto_shutdown"))
        self.t3.setText(t("naming_tmpl"))
        self.chk_sub.setText(t("subfolder"))
        self.chk_nfo.setText(t("create_nfo"))
        self.chk_thumb.setText(t("download_thumb"))
        self.chk_subs.setText(t("download_subs"))
        self.t_mp3.setText(t("mp3_quality"))
        self.t4.setText(t("proxy"))
        self.t5.setText(t("download_dir"))
        self.btn_dir.setText(t("browse"))
        self.btn_save.setText(f"💾 {t('save_settings')}")
        self.btn_yup.setText(f"🔄 {t('update_ytdlp')}")

    def _sel_dir(self): 
        d = QFileDialog.getExistingDirectory(self, t("browse"), self.in_dir.text())
        if d: self.in_dir.setText(d)

    def _save_settings(self):
        self.main_window.config.set("max_concurrent_downloads", int(self.sp_limit.currentText()))
        try: self.main_window.config.set("speed_limit_kbps", int(self.inp_speed.text()))
        except: self.main_window.config.set("speed_limit_kbps", 0)
        self.main_window.config.set("auto_shutdown", self.chk_shutdown.isChecked())
        self.main_window.config.set("naming_template", self.inp_tmpl.text())
        self.main_window.config.set("auto_subfolder_by_platform", self.chk_sub.isChecked())
        self.main_window.config.set("create_nfo", self.chk_nfo.isChecked())
        self.main_window.config.set("download_thumbnail", self.chk_thumb.isChecked())
        self.main_window.config.set("download_subs", self.chk_subs.isChecked())
        
        cookie_text = self.cb_cookies.currentText()
        cookie_val = "" if cookie_text == "Hiçbiri" else cookie_text.lower()
        self.main_window.config.set("browser_cookies", cookie_val)
        
        self.main_window.config.set("mp3_quality", self.cb_mp3.currentText())
        self.main_window.config.set("proxy", self.inp_proxy.text())
        self.main_window.config.set("download_dir", self.in_dir.text())
        self.main_window.search_view.status.setText(t("settings_saved"))

    def _update_ytdlp(self):
        self.main_window.search_view.status.setText(t("updating"))
        QApplication.processEvents()
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"], check=True)
            self.main_window.search_view.status.setText(t("update_success"))
        except Exception as e:
            self.main_window.search_view.status.setText(f"{t('update_error')} {e}")
