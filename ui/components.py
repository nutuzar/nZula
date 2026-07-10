import os
import subprocess
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QProgressBar, QMenu, QFileDialog
from PySide6.QtCore import Qt, Slot, QUrl
from PySide6.QtGui import QFont, QPixmap, QDesktopServices
from PySide6.QtNetwork import QNetworkRequest, QNetworkReply
from core.downloader import SingleDownloadWorker
from core.i18n import t
from ui.theme import *

class ImageLoader(QLabel):
    def __init__(self, thumb_url: str, video_url: str, manager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.thumb_url = thumb_url
        self.video_url = video_url
        self.setFixedSize(140, 100)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(f"background-color: {BG_COLOR}; border-radius: {BORDER_RADIUS}; color: {SUBTEXT_COLOR}; font-size: 11px;")
        self.setText("...")
        if self.thumb_url: self._start_download()

    def _start_download(self):
        req = QNetworkRequest(QUrl(self.thumb_url))
        req.setHeader(QNetworkRequest.KnownHeaders.UserAgentHeader, "Mozilla/5.0")
        self.reply = self.manager.get(req)
        self.reply.finished.connect(self._on_download_finished)

    def _on_download_finished(self):
        if self.reply.error() == QNetworkReply.NetworkError.NoError:
            pix = QPixmap()
            if pix.loadFromData(self.reply.readAll()):
                self.setPixmap(pix.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
                self.setText("")
        self.reply.deleteLater()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.video_url:
            QDesktopServices.openUrl(QUrl(self.video_url))

    def contextMenuEvent(self, event):
        if not self.pixmap(): return
        menu = QMenu(self)
        menu.setStyleSheet(f"background-color: {PANEL_COLOR}; color: {TEXT_COLOR}; border: 1px solid {BORDER_COLOR};")
        save_action = menu.addAction(t("download"))
        action = menu.exec(event.globalPos())
        if action == save_action:
            path, _ = QFileDialog.getSaveFileName(self, t("download"), "thumbnail.jpg", "Images (*.jpg *.png)")
            if path:
                self.pixmap().save(path)

class DownloadItemWidget(QFrame):
    def __init__(self, url: str, dict_key: str, title: str, parent_ui, parent=None):
        super().__init__(parent)
        self.url = url
        self.dict_key = dict_key
        self.title_text = title
        self.parent_ui = parent_ui
        self.final_file_path = ""
        self.is_finished = False
        self.setMinimumHeight(100)
        self.setStyleSheet(f"QFrame {{ background-color: {PANEL_COLOR}; border: 1px solid {BORDER_COLOR}; border-radius: {BORDER_RADIUS}; }}")
        self._build_ui()
        
    def _build_ui(self):
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        self.title_label = QLabel(self.title_text)
        self.title_label.setFont(QFont(FONT_FAMILY, 11, QFont.Weight.Bold))
        self.title_label.setStyleSheet(f"color: {TEXT_COLOR}; border: none;")
        
        self.resume_btn = QPushButton(f"🔄 {t('resume')}")
        self.resume_btn.setStyleSheet(f"QPushButton {{ background-color: {ACCENT_BLUE}; color: white; border-radius: 6px; padding: 6px 12px; font-weight: bold; border: none; }}")
        self.resume_btn.hide()
        self.resume_btn.clicked.connect(self._on_resume_clicked)
        
        self.cancel_btn = QPushButton(f"❌ {t('cancel')}")
        self.cancel_btn.setStyleSheet(f"QPushButton {{ background-color: {ACCENT_RED}; color: white; border-radius: 6px; padding: 6px 12px; font-weight: bold; border: none; }}")
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        
        top.addWidget(self.title_label, 1)
        top.addWidget(self.resume_btn)
        top.addWidget(self.cancel_btn)
        layout.addLayout(top)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(f"QProgressBar {{ background-color: {BG_COLOR}; border-radius: 4px; text-align: center; color: white; border: none; }} QProgressBar::chunk {{ background-color: {ACCENT_BLUE}; border-radius: 4px; }}")
        layout.addWidget(self.progress_bar)
        
        status = QHBoxLayout()
        self.speed_label = QLabel(f"{t('speed')} --")
        self.eta_label = QLabel(f"{t('remaining')} --")
        self.size_label = QLabel(f"{t('size')} --")
        for l in [self.speed_label, self.eta_label, self.size_label]: 
            l.setStyleSheet(f"color: {SUBTEXT_COLOR}; font-size: 11px; border: none;")
        
        status.addWidget(self.speed_label)
        status.addStretch()
        status.addWidget(self.eta_label)
        status.addStretch()
        status.addWidget(self.size_label)
        layout.addLayout(status)
        
    def _on_cancel_clicked(self): 
        self.cancel_btn.setEnabled(False)
        self.parent_ui.cancel_download(self.dict_key)
        
    def _on_resume_clicked(self):
        self.resume_btn.hide()
        self.cancel_btn.show()
        self.cancel_btn.setEnabled(True)
        self.speed_label.setText("🚀")
        self.parent_ui.resume_download(self.dict_key)
        
    @Slot(dict)
    def update_status(self, d: dict):
        self.progress_bar.setValue(int(d['percentage']))
        self.speed_label.setText(f"🚀 {d['speed']}")
        self.size_label.setText(f"📦 {d['downloaded_mb']} / {d['total_mb']} MB")
        
    def finalize_success(self, path):
        self.is_finished = True
        self.final_file_path = path
        self.progress_bar.setValue(100)
        self.speed_label.setText("✅")
        self.cancel_btn.show()
        self.resume_btn.hide()
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.setText(f"📂 {t('open_file')}")
        self.cancel_btn.setStyleSheet(f"background-color: {ACCENT_GREEN}; color: #11111b; border: none;")
        try: self.cancel_btn.clicked.disconnect()
        except: pass
        self.cancel_btn.clicked.connect(lambda: subprocess.run(['explorer', '/select,', os.path.normpath(self.final_file_path)]))
        self.parent_ui.db.save_download(self.url, self.title_text, self.final_file_path, "completed")
        self.parent_ui._start_queue()
        self.parent_ui.refresh_dashboard_stats()
        
    def finalize_error(self, msg):
        self.speed_label.setText(f"❌ {t('error')} / İptal Edildi")
        self.cancel_btn.setText("Sil")
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.setStyleSheet(f"background-color: {ACCENT_RED}; color: white; border: none;")
        try: self.cancel_btn.clicked.disconnect()
        except: pass
        self.cancel_btn.clicked.connect(self.deleteLater)
        self.resume_btn.show()
