import yt_dlp
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QStyle, QWidget
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtCore import QUrl, Qt, Signal, QThread
from core.i18n import t

class StreamFetcher(QThread):
    url_ready = Signal(str, dict)
    error_occurred = Signal(str)
    
    def __init__(self, url):
        super().__init__()
        self.url = url
        
    def run(self):
        # QMediaPlayer'in (QtMultimedia) çökmemesi için
        # zorla en uyumlu düz (DASH olmayan) mp4 formatını çekiyoruz.
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'best[ext=mp4][vcodec^=avc1]/best[ext=mp4]/best'
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
                stream_url = info.get('url')
                headers = info.get('http_headers', {})
                if stream_url:
                    self.url_ready.emit(stream_url, headers)
                else:
                    self.error_occurred.emit("Video linki alınamadı.")
        except Exception as e:
            self.error_occurred.emit(str(e))

class PreviewDialog(QDialog):
    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Önizleme (Dahili Oynatıcı)")
        self.resize(850, 480)
        self.setStyleSheet("background-color: #1c1c1e; color: #f2f2f7;")
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_loading = QLabel("Medya yükleniyor... Lütfen bekleyin.")
        self.lbl_loading.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.lbl_loading)
        
        self.video_widget = QVideoWidget()
        self.layout.addWidget(self.video_widget)
        self.video_widget.hide()
        
        # --- Oynatma Kontrolleri (Status Bar) ---
        self.controls_layout = QHBoxLayout()
        self.controls_layout.setContentsMargins(10, 10, 10, 10)
        
        self.btn_play = QPushButton("⏸")
        self.btn_play.setFixedSize(40, 40)
        self.btn_play.setStyleSheet("background-color: #0a84ff; color: white; border-radius: 20px; font-weight: bold; font-size: 16px;")
        self.btn_play.clicked.connect(self._toggle_play)
        
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal { border: 1px solid #38383a; height: 8px; background: #2c2c2e; border-radius: 4px; }
            QSlider::sub-page:horizontal { background: #30d158; border-radius: 4px; }
            QSlider::handle:horizontal { background: #f2f2f7; width: 14px; margin-top: -3px; margin-bottom: -3px; border-radius: 7px; }
        """)
        self.slider.sliderMoved.connect(self._set_position)
        
        self.lbl_time = QLabel("00:00 / 00:00")
        self.lbl_time.setStyleSheet("color: #aeaeb2; font-weight: bold;")
        
        self.controls_layout.addWidget(self.btn_play)
        self.controls_layout.addWidget(self.slider)
        self.controls_layout.addWidget(self.lbl_time)
        
        self.controls_container = QWidget()
        self.controls_container.setLayout(self.controls_layout)
        self.controls_container.setStyleSheet("background-color: #2c2c2e; border-top: 1px solid #38383a;")
        self.layout.addWidget(self.controls_container)
        self.controls_container.hide()
        # ----------------------------------------
        
        self.audio_output = QAudioOutput(self)
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)
        self.player.errorOccurred.connect(self._on_player_error)
        self.player.positionChanged.connect(self._position_changed)
        self.player.durationChanged.connect(self._duration_changed)
        
        self.fetcher = StreamFetcher(url)
        self.fetcher.url_ready.connect(self._on_url_ready)
        self.fetcher.error_occurred.connect(self._on_error)
        self.fetcher.start()

    def _on_url_ready(self, stream_url, headers):
        self.stream_url = stream_url
        self.stream_headers = headers
        self.lbl_loading.hide()
        self.video_widget.show()
        self.controls_container.show()
        self.player.setSource(QUrl(stream_url))
        self.player.play()
        
    def _toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.btn_play.setText("▶")
        else:
            self.player.play()
            self.btn_play.setText("⏸")

    def _position_changed(self, position):
        self.slider.blockSignals(True)
        self.slider.setValue(position)
        self.slider.blockSignals(False)
        self._update_time_label()

    def _duration_changed(self, duration):
        self.slider.setRange(0, duration)
        self._update_time_label()

    def _set_position(self, position):
        self.player.setPosition(position)

    def _update_time_label(self):
        pos = self.player.position() // 1000
        dur = self.player.duration() // 1000
        self.lbl_time.setText(f"{pos//60:02d}:{pos%60:02d} / {dur//60:02d}:{dur%60:02d}")

    def _on_player_error(self, error, error_string):
        if not hasattr(self, 'stream_url'): return
        import subprocess
        self.player.stop()
        self.video_widget.hide()
        self.controls_container.hide()
        self.lbl_loading.show()
        self.lbl_loading.setText(f"Dahili oynatıcı hatası: {error_string}\nHarici oynatıcı (FFplay) başlatılıyor...")
        try:
            cmd = ["ffplay"]
            if hasattr(self, 'stream_headers') and self.stream_headers:
                header_str = "".join([f"{k}: {v}\r\n" for k, v in self.stream_headers.items()])
                cmd.extend(["-headers", header_str])
                
            cmd.extend([
                "-i", self.stream_url, 
                "-autoexit", "-window_title", "nZula Harici Önizleme",
                "-loglevel", "quiet"
            ])
            
            subprocess.Popen(cmd)
            self.lbl_loading.setText("Harici oynatıcıda (FFplay) oynatılıyor.\nPencereyi kapatabilirsiniz.")
        except Exception as e:
            self.lbl_loading.setText(f"Harici oynatıcı da başlatılamadı:\n{e}")

    def _on_error(self, err):
        self.lbl_loading.setText(f"Hata: {err}")

    def closeEvent(self, event):
        self.player.stop()
        if self.fetcher.isRunning():
            self.fetcher.terminate()
        super().closeEvent(event)
