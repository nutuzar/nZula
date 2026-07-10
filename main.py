import sys
import os
import subprocess
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QStackedWidget, QFrame, QMessageBox, QButtonGroup
)
from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtGui import QFont, QDesktopServices
from PySide6.QtNetwork import QNetworkAccessManager
from loguru import logger
import sys, os
logger.add(os.path.join(os.path.expanduser("~"), "Downloads", "nZula", "nzula.log"), rotation="1 MB", level="DEBUG")

from core.downloader import SingleDownloadWorker
from core.database import DatabaseManager
from core.config import ConfigManager
from core.previewer import PreviewDialog
from core.i18n import t, set_lang

from ui.theme import *
from ui.search_view import SearchView
from ui.download_view import DownloadView
from ui.history_view import HistoryView
from ui.settings_view import SettingsView
from ui.about_view import AboutView
from ui.components import DownloadItemWidget

class MainUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.config = ConfigManager()
        set_lang(self.config.get("lang"))
        
        self.setWindowTitle("nZula - v1.0")
        self.resize(1300, 850)
        self.setMinimumSize(800, 600)
        self.setStyleSheet(f"QMainWindow {{ background-color: {BG_COLOR}; }}")
        
        self.network_manager = QNetworkAccessManager(self)
        self.search_worker = None
        self.download_workers = {}
        self.download_widgets = {}
        
        self._init_ui()
        self._setup_clipboard()

    def _setup_clipboard(self):
        self.clipboard = QApplication.clipboard()
        self.last_clipboard_text = self.clipboard.text().strip()
        
        # Check initial clipboard content
        self._on_clipboard_changed(self.last_clipboard_text)
        
        self.clipboard_timer = QTimer(self)
        self.clipboard_timer.timeout.connect(self._check_clipboard)
        self.clipboard_timer.start(1000)

    def _check_clipboard(self):
        text = self.clipboard.text().strip()
        if text != self.last_clipboard_text:
            self.last_clipboard_text = text
            self._on_clipboard_changed(text)
        
    def _on_clipboard_changed(self, text):
        if not text.startswith("http"): return
        
        lower_text = text.lower()
        supported = ["vk.com", "vkvideo.ru", "ok.ru", "bilibili", "rutube.ru", "dailymotion.com", "youtube.com", "youtu.be", "archive.org"]
        if any(d in lower_text for d in supported):
            # Switch to search view and append it as a card
            self._switch(0, self.btn_search)
            self.search_view.status.setText(f"Panodan yakalandı: {text[:40]}...")
            self.search_view._append_clipboard_link(text)

    def _init_ui(self):
        cw = QWidget()
        self.setCentralWidget(cw)
        self.main_layout = QVBoxLayout(cw)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        self._setup_top_nav()
        self._setup_pages()
        self.retranslate_ui()

    def _setup_top_nav(self):
        self.top_nav = QFrame()
        self.top_nav.setFixedHeight(70)
        self.top_nav.setStyleSheet(f"background-color: {PANEL_COLOR}; border-bottom: 1px solid {BORDER_COLOR};")
        layout = QHBoxLayout(self.top_nav)
        layout.setContentsMargins(20, 0, 20, 0)
        
        title = QLabel("nZula v1.0")
        title.setFont(QFont(FONT_FAMILY, 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ACCENT_BLUE}; margin-right: 30px; border: none;")
        layout.addWidget(title)
        
        self.btn_search = self._menu_btn(t("menu_search"), True)
        self.btn_downloads = self._menu_btn(t("menu_downloads"), False)
        self.btn_history = self._menu_btn(t("menu_history"), False)
        self.btn_settings = self._menu_btn(t("menu_settings"), False)
        self.btn_about = self._menu_btn(t("menu_about"), False)
        
        for b in [self.btn_search, self.btn_downloads, self.btn_history, self.btn_settings, self.btn_about]:
            layout.addWidget(b)
        
        layout.addStretch()
        
        lang_layout = QHBoxLayout()
        self.btn_tr = QPushButton("TR")
        self.btn_tr.setCheckable(True)
        self.btn_tr.setChecked(self.config.get("lang") == "tr")
        
        self.btn_en = QPushButton("EN")
        self.btn_en.setCheckable(True)
        self.btn_en.setChecked(self.config.get("lang") == "en")
        
        self.lang_group = QButtonGroup(self)
        self.lang_group.addButton(self.btn_tr)
        self.lang_group.addButton(self.btn_en)
        
        for btn in [self.btn_tr, self.btn_en]:
            btn.setStyleSheet(f"""
                QPushButton {{ color: {SUBTEXT_COLOR}; font-weight: bold; background: {BG_COLOR}; border: 1px solid {BORDER_COLOR}; border-radius: 4px; padding: 4px 8px; }}
                QPushButton:checked {{ color: white; background: {ACCENT_BLUE}; border: none; }}
            """)
            lang_layout.addWidget(btn)
            
        self.btn_tr.clicked.connect(lambda: self._change_lang("tr"))
        self.btn_en.clicked.connect(lambda: self._change_lang("en"))
        layout.addLayout(lang_layout)
        
        self.main_layout.addWidget(self.top_nav)
        
        self.btn_search.clicked.connect(lambda: self._switch(0, self.btn_search))
        self.btn_downloads.clicked.connect(lambda: self._switch(1, self.btn_downloads))
        self.btn_history.clicked.connect(lambda: self._switch(2, self.btn_history))
        self.btn_settings.clicked.connect(lambda: self._switch(3, self.btn_settings))
        self.btn_about.clicked.connect(lambda: self._switch(4, self.btn_about))

    def _menu_btn(self, t_text, chk):
        b = QPushButton(t_text)
        b.setCheckable(True)
        b.setChecked(chk)
        b.setStyleSheet(f"""
            QPushButton {{ color: {SUBTEXT_COLOR}; font-family: {FONT_FAMILY}; padding: 10px 15px; border: none; font-size: 14px; font-weight: 600; background: transparent; }}
            QPushButton:hover {{ color: {TEXT_COLOR}; }}
            QPushButton:checked {{ color: {ACCENT_BLUE}; border-bottom: 3px solid {ACCENT_BLUE}; border-radius: 0px; }}
        """)
        return b

    def _setup_pages(self):
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background-color: {BG_COLOR};")
        self.main_layout.addWidget(self.stack)
        
        self.search_view = SearchView(self)
        self.download_view = DownloadView(self)
        self.history_view = HistoryView(self)
        self.settings_view = SettingsView(self)
        self.about_view = AboutView(self)
        
        for p in [self.search_view, self.download_view, self.history_view, self.settings_view, self.about_view]:
            self.stack.addWidget(p)

    def _switch(self, i, b): 
        self.stack.setCurrentIndex(i)
        for btn in [self.btn_search, self.btn_downloads, self.btn_history, self.btn_settings, self.btn_about]: 
            btn.setChecked(False)
        b.setChecked(True)
        if b == self.btn_history:
            self.history_view.refresh_history()

    def _change_lang(self, lang):
        set_lang(lang)
        self.config.set("lang", lang)
        self.retranslate_ui()

    def retranslate_ui(self):
        self.btn_search.setText(f"🔍 {t('menu_search')}")
        self.btn_downloads.setText(f"⬇️ {t('menu_downloads')}")
        self.btn_history.setText(f"📚 {t('menu_history')}")
        self.btn_settings.setText(f"⚙️ {t('menu_settings')}")
        self.btn_about.setText(f"ℹ️ {t('menu_about')}")
        
        self.search_view.retranslate_ui()
        self.download_view.retranslate_ui()
        self.history_view.retranslate_ui()
        self.settings_view.retranslate_ui()
        self.about_view.retranslate_ui()

    def refresh_dashboard_stats(self):
        self.search_view.refresh_stats()

    def _start_queue(self):
        max_active = self.config.get("max_concurrent_downloads")
        active_count = sum(1 for w in self.download_workers.values() if w.isRunning())
        
        if active_count == 0 and len(self.download_workers) > 0:
            all_done = all(self.download_widgets[u].is_finished for u in self.download_workers)
            if all_done and self.config.get("auto_shutdown"):
                if sys.platform == "win32":
                    os.system("shutdown /s /t 60")
                else:
                    os.system("shutdown -h +1")
                # Giyotin İptal Mekanizması
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Icon.Warning)
                msg_box.setWindowTitle("Sistem Kapanıyor")
                msg_box.setText("Tüm indirmeler tamamlandı. Bilgisayar 60 saniye içinde kapatılacak!")
                abort_btn = msg_box.addButton("Kapanmayı İptal Et", QMessageBox.ButtonRole.RejectRole)
                msg_box.exec()
                if msg_box.clickedButton() == abort_btn:
                    if sys.platform == "win32":
                        os.system("shutdown /a")
                    else:
                        os.system("killall shutdown")
                    self.search_view.status.setText("Otomatik kapanma iptal edildi.")
                return
                
        for dict_key, w in self.download_workers.items():
            if active_count >= max_active: break
            if not w.isRunning() and not self.download_widgets[dict_key].is_finished:
                self.download_widgets[dict_key].speed_label.setText("🚀")
                w.start()
                active_count += 1
                
    def _preview_media(self, url):
        self.preview_window = PreviewDialog(url, self)
        self.preview_window.show()

    def _add_dl(self, u, title_text, fmt='1080p', auto_start=True):
        dict_key = f"{u}_{fmt}"
        if dict_key in self.download_workers: return
        w_ui = DownloadItemWidget(u, dict_key, title_text, self)
        self.download_view.add_widget(w_ui)
        self.download_widgets[dict_key] = w_ui
        
        download_dir = self.config.get("download_dir")
        work = SingleDownloadWorker(u, download_dir, fmt)
        self.download_workers[dict_key] = work
        
        work.signals.progress_updated.connect(lambda url, d, key=dict_key: self.download_widgets[key].update_status(d))
        work.signals.download_finished.connect(lambda url, path, key=dict_key: self.download_widgets[key].finalize_success(path))
        work.signals.download_error.connect(lambda url, msg, key=dict_key: self.download_widgets[key].finalize_error(msg))
        
        if auto_start:
            work.start()
        else:
            self.download_widgets[dict_key].speed_label.setText("⏳")
        self._switch(1, self.btn_downloads)

    def cancel_download(self, dict_key): 
        if dict_key in self.download_workers:
            self.download_workers[dict_key].cancel()

    def resume_download(self, dict_key):
        if dict_key in self.download_workers:
            # İşçi iptal edildikten veya hata verdikten sonra thread sonlanmış olabilir.
            # Yt-dlp aynı klasörde yarım kalan dosyayı bulduğu an .part üzerinden devam edecektir.
            old_worker = self.download_workers[dict_key]
            
            # Yeni worker olustur (Thread'ler tekrar start edilemez)
            new_worker = SingleDownloadWorker(old_worker.url, old_worker.output_dir, old_worker.format)
            self.download_workers[dict_key] = new_worker
            
            new_worker.signals.progress_updated.connect(lambda url, d, key=dict_key: self.download_widgets[key].update_status(d))
            new_worker.signals.download_finished.connect(lambda url, path, key=dict_key: self.download_widgets[key].finalize_success(path))
            new_worker.signals.download_error.connect(lambda url, msg, key=dict_key: self.download_widgets[key].finalize_error(msg))
            
            new_worker.start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainUI()
    window.show()
    sys.exit(app.exec())