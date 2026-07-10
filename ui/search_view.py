import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, 
    QCheckBox, QComboBox, QScrollArea, QGridLayout, QFrame, QSizePolicy, QDialog, QTextEdit, QDialogButtonBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from core.i18n import t
from core.searcher import MultiPlatformSearchWorker, MetadataFetchWorker
from ui.theme import *
from ui.components import ImageLoader
from functools import partial

class BatchDownloadDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("batch_download"))
        self.setFixedSize(500, 400)
        self.setStyleSheet(f"background-color: {BG_COLOR}; color: {TEXT_COLOR};")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("URLs:"))
        self.text_edit = QTextEdit()
        self.text_edit.setStyleSheet(f"background-color: {PANEL_COLOR}; border: 1px solid {BORDER_COLOR}; color: {TEXT_COLOR}; font-size: 14px;")
        layout.addWidget(self.text_edit)
        
        row = QHBoxLayout()
        row.addWidget(QLabel("Format:"))
        self.fmt_combo = QComboBox()
        self.fmt_combo.addItems(["1080p", "720p", "480p", "Audio (MP3)"])
        self.fmt_combo.setStyleSheet(f"background-color: {PANEL_COLOR}; border: 1px solid {BORDER_COLOR}; color: {TEXT_COLOR};")
        row.addWidget(self.fmt_combo)
        layout.addLayout(row)
        
        self.btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.btns.setStyleSheet(f"QPushButton {{ background-color: {PANEL_COLOR}; border: 1px solid {BORDER_COLOR}; color: {TEXT_COLOR}; padding: 6px 12px; border-radius: 6px; }}")
        self.btns.accepted.connect(self.accept)
        self.btns.rejected.connect(self.reject)
        layout.addWidget(self.btns)

class SearchView(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.all_search_results = []
        self.current_row = 0
        self.current_col = 0
        self.max_columns = 4
        self.card_widgets = {}
        self.metadata_worker = None
        self.clipboard_workers = []
        self._init_ui()

    def _init_ui(self):
        l = QVBoxLayout(self)
        l.setContentsMargins(40, 20, 40, 30)
        l.setSpacing(15)
        
        # Dashboard banner kaldırıldı (Kullanıcı isteği üzerine)

        search_row = QHBoxLayout()
        self.in_s = QLineEdit()
        self.in_s.setPlaceholderText(t("search_placeholder"))
        self.in_s.setClearButtonEnabled(True)
        self.in_s.setStyleSheet(f"background-color: {PANEL_COLOR}; color: {TEXT_COLOR}; border: 1px solid {BORDER_COLOR}; border-radius: 8px; padding: 12px; font-size: 14px;")
        search_row.addWidget(self.in_s)
        self.btn_s = QPushButton(f"🔍 {t('search')}")
        self.btn_s.setStyleSheet(f"background-color: {ACCENT_BLUE}; color: white; border-radius: 8px; font-weight: bold; font-size: 14px; padding: 12px 24px;")
        self.btn_batch = QPushButton(f"📑 {t('batch_download')}")
        self.btn_batch.setStyleSheet(f"background-color: {PANEL_COLOR}; color: {TEXT_COLOR}; border: 1px solid {BORDER_COLOR}; border-radius: 8px; font-weight: bold; font-size: 14px; padding: 12px 24px;")
        self.btn_batch.clicked.connect(self._open_batch_dialog)
        
        self.btn_clear = QPushButton("🗑️ Temizle")
        self.btn_clear.setStyleSheet(f"background-color: {ACCENT_RED}; color: white; border-radius: 8px; font-weight: bold; font-size: 14px; padding: 12px 24px;")
        self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.clicked.connect(self.clear_results)
        
        search_row.addWidget(self.btn_s)
        search_row.addWidget(self.btn_batch)
        search_row.addWidget(self.btn_clear)
        l.addLayout(search_row)
        
        plat_l = QHBoxLayout()
        self.plat_lbl = QLabel(f"<b>{t('sources')}</b> (Dahili):")
        self.plat_lbl.setStyleSheet(f"color: {TEXT_COLOR};")
        plat_l.addWidget(self.plat_lbl)
        
        from PySide6.QtGui import QIcon, QDesktopServices
        from PySide6.QtCore import QSize, QUrl
        import os, sys, urllib.parse
        
        def resource_path(relative_path):
            if hasattr(sys, '_MEIPASS'):
                return os.path.join(sys._MEIPASS, relative_path)
            return os.path.join(os.path.abspath("."), relative_path)
        
        def set_icon(w, name):
            p = resource_path(os.path.join("assets", name))
            if os.path.exists(p):
                w.setIcon(QIcon(p))
                if hasattr(w, "setIconSize"): w.setIconSize(QSize(20, 20))
        
        self.c_yt = QCheckBox(" YouTube"); self.c_yt.setChecked(True)
        set_icon(self.c_yt, "youtube.ico")
        self.c_arc = QCheckBox(" Archive.org"); self.c_arc.setChecked(True)
        set_icon(self.c_arc, "internetarchive.png")
        
        for c in [self.c_yt, self.c_arc]: 
            c.setStyleSheet(f"color: {SUBTEXT_COLOR}; font-weight: bold;")
            plat_l.addWidget(c)
            
        plat_l.addStretch()
        l.addLayout(plat_l)
        
        ext_l = QHBoxLayout()
        self.ext_lbl = QLabel("<b>Harici Tarayıcı Taraması:</b>")
        self.ext_lbl.setStyleSheet(f"color: {TEXT_COLOR};")
        ext_l.addWidget(self.ext_lbl)
        
        def open_external(url_template):
            q = urllib.parse.quote(self.in_s.text().strip())
            if q: QDesktopServices.openUrl(QUrl(url_template.format(q=q)))

        self.btn_vk = QPushButton(" VK")
        self.btn_vk.clicked.connect(lambda: open_external("https://vk.com/video?q={q}"))
        set_icon(self.btn_vk, "vk.png")
        
        self.btn_ok = QPushButton(" ok.ru")
        self.btn_ok.clicked.connect(lambda: open_external("https://ok.ru/search?st.query={q}"))
        set_icon(self.btn_ok, "okru.ico")
        
        self.btn_bili = QPushButton(" Bilibili")
        self.btn_bili.clicked.connect(lambda: open_external("https://search.bilibili.com/video?keyword={q}"))
        set_icon(self.btn_bili, "bilibili.svg")
        
        self.btn_ru = QPushButton(" RuTube")
        self.btn_ru.clicked.connect(lambda: open_external("https://rutube.ru/search/?query={q}"))
        set_icon(self.btn_ru, "rutube.png")
        
        self.btn_dm = QPushButton(" Dailymotion")
        self.btn_dm.clicked.connect(lambda: open_external("https://www.dailymotion.com/search/{q}/videos"))
        set_icon(self.btn_dm, "dailymotion.jpg")

        for b in [self.btn_vk, self.btn_ok, self.btn_bili, self.btn_ru, self.btn_dm]:
            b.setStyleSheet(f"background-color: {PANEL_COLOR}; color: {SUBTEXT_COLOR}; border: 1px solid {BORDER_COLOR}; border-radius: 4px; padding: 6px 14px; font-weight: bold; text-align: center;")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            ext_l.addWidget(b)
            
        ext_l.addStretch()
        
        self.dur_filter = QComboBox()
        self.dur_filter.addItems([t("duration_all"), t("duration_30"), t("duration_60"), t("duration_90"), t("duration_120")])
        self.dur_filter.setStyleSheet(f"background-color: {PANEL_COLOR}; color: {TEXT_COLOR}; border: 1px solid {BORDER_COLOR}; border-radius: 6px; padding: 6px;")
        self.dur_filter.currentIndexChanged.connect(self._apply_duration_filter)
        ext_l.addWidget(self.dur_filter)
        
        l.addLayout(ext_l)
        
        status_row = QHBoxLayout()
        self.status = QLabel(t("ready"))
        self.status.setStyleSheet(f"color: {SUBTEXT_COLOR};")
        status_row.addWidget(self.status)
        status_row.addStretch()
        l.addLayout(status_row)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; } QScrollBar:vertical { background: transparent; width: 10px; } QScrollBar::handle:vertical { background: #48484a; border-radius: 5px; }")
        self.res_c = QWidget()
        self.res_c.setStyleSheet("background: transparent;")
        self.res_l = QGridLayout(self.res_c)
        self.scroll.setWidget(self.res_c)
        l.addWidget(self.scroll)
        
        self.btn_s.clicked.connect(self._do_search)
        self.in_s.returnPressed.connect(self._do_search)
        self.refresh_stats()

    def refresh_stats(self):
        pass  # Dashboard kaldırıldığı için pasif

    def retranslate_ui(self):
        self.in_s.setPlaceholderText(t("search_placeholder"))
        self.btn_s.setText(f"🔍 {t('search')}")
        self.btn_batch.setText(f"📑 {t('batch_download')}")
        self.plat_lbl.setText(t("sources"))
        
        old_idx = self.dur_filter.currentIndex()
        self.dur_filter.blockSignals(True)
        self.dur_filter.clear()
        self.dur_filter.addItems([t("duration_all"), t("duration_30"), t("duration_60"), t("duration_90"), t("duration_120")])
        self.dur_filter.setCurrentIndex(old_idx)
        self.dur_filter.blockSignals(False)
        self.status.setText(t("ready"))

    def _open_batch_dialog(self):
        dlg = BatchDownloadDialog(self)
        if dlg.exec():
            urls = dlg.text_edit.toPlainText().strip().split("\n")
            fmt = dlg.fmt_combo.currentText()
            for u in urls:
                u = u.strip()
                if u:
                    self.main_window._add_dl(u, f"Batch: {u[:25]}...", fmt, True)

    def _do_search(self):
        q = self.in_s.text().strip()
        if not q: return
        
        self.clear_results()
        
        p = []
        if self.c_yt.isChecked(): p.append("youtube")
        if self.c_arc.isChecked(): p.append("archive.org")
        
        self.main_window.search_worker = MultiPlatformSearchWorker(q, p)
        self.main_window.search_worker.signals.result_found.connect(self._add_card)
        self.main_window.search_worker.signals.search_completed.connect(self._on_search_completed)
        self.main_window.search_worker.start()
        self.status.setText(t("searching"))

    def clear_results(self):
        if self.main_window.search_worker and self.main_window.search_worker.isRunning(): 
            self.main_window.search_worker.cancel()
            self.main_window.search_worker.wait()
            
        if self.metadata_worker and self.metadata_worker.isRunning():
            self.metadata_worker.cancel()
            self.metadata_worker.wait()
            
        for w in self.clipboard_workers:
            if w.isRunning():
                w.cancel()
                w.wait()
        self.clipboard_workers.clear()
            
        while self.res_l.count(): 
            w = self.res_l.takeAt(0).widget()
            w.deleteLater() if w else None
            
        self.card_widgets.clear()
        self.all_search_results.clear()
        self.current_row, self.current_col = 0, 0
        self.status.setText(t("ready"))

    def _append_clipboard_link(self, url):
        # Do not clear the existing grid or search_results.
        # Just spawn a worker to fetch this single URL.
        worker = MultiPlatformSearchWorker(url, [])
        self.clipboard_workers.append(worker)
        worker.signals.result_found.connect(self._add_card)
        worker.signals.search_completed.connect(lambda r, w=worker: self._on_clipboard_search_done(w))
        worker.start()

    def _on_clipboard_search_done(self, worker):
        if worker in self.clipboard_workers:
            self.clipboard_workers.remove(worker)
        # Re-trigger metadata worker for any newly added cards that have "?" filesize
        self._on_search_completed(None)

    def _on_search_completed(self, total_results):
        self.status.setText(t("search_done"))
        urls_to_fetch = [m['url'] for m in self.all_search_results if m.get('filesize', '?') == '?']
        if urls_to_fetch:
            self.metadata_worker = MetadataFetchWorker(urls_to_fetch)
            self.metadata_worker.signals.metadata_fetched.connect(self._update_card_metadata)
            self.metadata_worker.signals.fetch_completed.connect(self._on_fetch_completed)
            self.metadata_worker.start()

    def _on_fetch_completed(self):
        # Refresh the layout if a filter is active so newly discovered durations appear
        if self.dur_filter.currentIndex() > 0:
            self._apply_duration_filter()

    def _update_card_metadata(self, url, new_meta):
        # Update the underlying data
        for m in self.all_search_results:
            if m['url'] == url:
                m['filesize'] = new_meta['filesize']
                m['resolutions'] = new_meta['resolutions']
                m['duration'] = new_meta['duration']
                break
                
        # Update UI if widget still exists
        if url in self.card_widgets:
            w = self.card_widgets[url]
            old_text = w['info_lbl'].text()
            parts = old_text.split(" | ")
            if len(parts) >= 3:
                parts[1] = f"⏱️ {new_meta['duration']}"
                parts[2] = f"📦 {new_meta['filesize']}"
                w['info_lbl'].setText(" | ".join(parts))
            
            # fcb update
            res_list = new_meta.get('resolutions', [])
            if res_list:
                w['fcb'].clear()
                w['fcb'].addItems(res_list)
                w['fcb'].addItem("Audio (MP3)")
                w['fcb'].setCurrentIndex(0)
            elif w['fcb'].itemText(0) == "⏳ Çözülüyor...":
                w['fcb'].setItemText(0, "Varsayılan")

    def _apply_duration_filter(self):
        while self.res_l.count(): 
            w = self.res_l.takeAt(0).widget()
            w.deleteLater() if w else None
        self.current_row, self.current_col = 0, 0
        
        dur_text = self.dur_filter.currentText()
        min_dur = 0
        if "> 30" in dur_text: min_dur = 1800
        elif "> 60" in dur_text: min_dur = 3600
        elif "> 90" in dur_text: min_dur = 5400
        elif "> 120" in dur_text: min_dur = 7200

        for m in self.all_search_results:
            sec = self._parse_duration(m['duration'])
            if min_dur == 0 or sec >= min_dur:
                self._render_single_card(m)

    def _parse_duration(self, dur_str):
        if not dur_str or ":" not in dur_str: return 0
        parts = dur_str.split(":")
        sec = 0
        try:
            if len(parts) == 3: sec = int(parts[0])*3600 + int(parts[1])*60 + int(parts[2])
            elif len(parts) == 2: sec = int(parts[0])*60 + int(parts[1])
        except: pass
        return sec

    def _add_card(self, m):
        self.all_search_results.append(m)
        dur_text = self.dur_filter.currentText()
        min_dur = 0
        if "> 30" in dur_text: min_dur = 1800
        elif "> 60" in dur_text: min_dur = 3600
        elif "> 90" in dur_text: min_dur = 5400
        elif "> 120" in dur_text: min_dur = 7200
        sec = self._parse_duration(m['duration'])
        if min_dur == 0 or sec >= min_dur:
            self._render_single_card(m)

    def _render_single_card(self, m):
        c = QFrame()
        c.setMinimumSize(250, 210)
        c.setMaximumHeight(260)
        c.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        c.setStyleSheet(f"QFrame {{ background-color: {PANEL_COLOR}; border-radius: {BORDER_RADIUS}; border: 1px solid {BORDER_COLOR}; }}")
        
        btn_close = QPushButton("✖", c)
        btn_close.setFixedSize(30, 30)
        btn_close.setStyleSheet("background: rgba(30,30,46,0.8); color: #ff5555; border-radius: 15px; font-size: 16px; font-weight: bold; padding: 0; border: 1px solid #ff5555;")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.raise_()
        
        def remove_card():
            if m in self.all_search_results:
                self.all_search_results.remove(m)
            if m['url'] in self.card_widgets:
                del self.card_widgets[m['url']]
            self._apply_duration_filter()
            
        btn_close.clicked.connect(remove_card)
        
        def c_resize(event):
            from PySide6.QtWidgets import QFrame
            QFrame.resizeEvent(c, event)
            btn_close.move(c.width() - 35, 5)
        c.resizeEvent = c_resize
        
        l = QVBoxLayout(c)
        l.setContentsMargins(15, 15, 15, 15)
        
        img_row = QHBoxLayout()
        img = ImageLoader(m['thumbnail'], m['url'], self.main_window.network_manager)
        img_row.addWidget(img)
        l.addLayout(img_row)
        
        ti = QLabel(m['title'])
        ti.setWordWrap(True)
        ti.setFont(QFont(FONT_FAMILY, 10, QFont.Weight.Bold))
        ti.setStyleSheet(f"color: {TEXT_COLOR}; border: none;")
        ti.setFixedHeight(40)
        l.addWidget(ti)
        
        f_size = m.get('filesize', '?')
        if f_size == '?': f_size = "⏳"
        info_lbl = QLabel(f"{m['platform']} | ⏱️ {m['duration']} | 📦 {f_size}")
        info_lbl.setStyleSheet(f"color: {SUBTEXT_COLOR}; font-size: 11px; border: none;")
        l.addWidget(info_lbl)
        
        bot_row = QHBoxLayout()
        fcb = QComboBox()
        res_list = m.get('resolutions', [])
        if res_list:
            fcb.addItems(res_list)
        elif m.get('filesize', '?') == '?':
            fcb.addItems(["⏳ Çözülüyor...", "1080p", "720p", "480p", "360p"])
        else:
            fcb.addItems(["1080p", "720p", "480p", "360p"])
        fcb.addItem("Audio (MP3)")
        
        self.card_widgets[m['url']] = {'info_lbl': info_lbl, 'fcb': fcb}
        
        fcb.setStyleSheet(f"background-color: {BG_COLOR}; color: {TEXT_COLOR}; border-radius: 4px; padding: 4px; border: none;")
        b_d = QPushButton(f"⬇️ {t('download')}")
        b_d.setStyleSheet(f"background-color: {ACCENT_GREEN}; color: #11111b; border-radius: 6px; padding: 6px; font-weight: bold; border: none;")
        b_p = QPushButton(f"👁️ {t('preview')}")
        b_p.setStyleSheet(f"background-color: {ACCENT_BLUE}; color: white; border-radius: 6px; padding: 6px; font-weight: bold; border: none;")
        
        def do_download(url, title, cb, *args):
            self.main_window._add_dl(url, title, cb.currentText(), True)
            
        def do_preview(url, *args):
            self.main_window._preview_media(url)
            
        b_d.clicked.connect(partial(do_download, m['url'], m['title'], fcb))
        b_p.clicked.connect(partial(do_preview, m['url']))
        
        bot_row.addWidget(fcb)
        bot_row.addWidget(b_d)
        bot_row.addWidget(b_p)
        l.addLayout(bot_row)
        
        self.res_l.addWidget(c, self.current_row, self.current_col, Qt.AlignTop | Qt.AlignLeft)
        self.current_col += 1
        if self.current_col >= self.max_columns: 
            self.current_col = 0
            self.current_row += 1
