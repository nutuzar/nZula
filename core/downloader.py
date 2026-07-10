import os
import sys
import traceback
from typing import Dict, Any, Optional
from PySide6.QtCore import QThread, Signal, QObject, QMutex, QMutexLocker
from loguru import logger
import yt_dlp
import json
import xml.etree.ElementTree as ET
from core.config import ConfigManager

class DownloaderSignals(QObject):
    download_started = Signal(str, dict)
    progress_updated = Signal(str, dict)
    download_finished = Signal(str, str)
    download_error = Signal(str, str)
    log_message = Signal(str, str, str)

class YTSageLoggerInterceptor:
    def __init__(self, url: str, signals: DownloaderSignals):
        self.url = url
        self.signals = signals

    def debug(self, msg: str) -> None:
        if "[debug]" not in msg and not msg.startswith('['):
            self.signals.log_message.emit(self.url, "DEBUG", msg)

    def info(self, msg: str) -> None:
        self.signals.log_message.emit(self.url, "INFO", msg)

    def warning(self, msg: str) -> None:
        self.signals.log_message.emit(self.url, "WARNING", msg)

    def error(self, msg: str) -> None:
        self.signals.log_message.emit(self.url, "ERROR", msg)

class SingleDownloadWorker(QThread):
    def __init__(self, url: str, download_dir: str, format_quality: str = "1080p", download_subs: bool = False, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.url = url
        self.download_dir = download_dir
        self.format_quality = format_quality
        self.signals = DownloaderSignals()
        self._is_cancelled = False
        self._mutex = QMutex()
        self.config = ConfigManager()
        os.makedirs(self.download_dir, exist_ok=True)

    def cancel(self) -> None:
        with QMutexLocker(self._mutex):
            self._is_cancelled = True

    def _progress_hook(self, d: Dict[str, Any]) -> None:
        with QMutexLocker(self._mutex):
            if self._is_cancelled:
                raise yt_dlp.utils.DownloadCancelled("KullaniciIptalIstegi")

        if d.get('status') == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)
            percentage = (downloaded / total * 100) if total > 0 else 0
            
            speed = d.get('speed', 0)
            speed_str = f"{speed / 1048576:.2f} MB/s" if speed and speed > 1048576 else f"{speed / 1024:.2f} KB/s" if speed else "0 KB/s"

            self.signals.progress_updated.emit(self.url, {
                'status': 'downloading',
                'percentage': round(percentage, 1),
                'speed': speed_str,
                'eta': "Hesaplanıyor...",
                'downloaded_mb': f"{downloaded / 1048576:.1f}",
                'total_mb': f"{total / 1048576:.1f}" if total else "?"
            })
        elif d['status'] == 'finished':
            self.signals.progress_updated.emit(self.url, {
                'percentage': 100,
                'speed': 'Dönüştürülüyor...' if self.format_quality == "Audio (MP3)" else 'İşleniyor...',
                'downloaded_mb': '...',
                'total_mb': '...'
            })

    def run(self) -> None:
        if self.format_quality == "Audio (MP3)":
            fmt_str = 'bestaudio/best'
        else:
            height = "".join([c for c in self.format_quality if c.isdigit()])
            if height:
                fmt_str = f'bestvideo[height<={height}]+bestaudio/best'
            else:
                fmt_str = 'bestvideo[height<=1080]+bestaudio/best'

        outtmpl_str = self.config.get("naming_template")
        if self.config.get("auto_subfolder_by_platform"):
            outtmpl_str = os.path.join('%(extractor)s', outtmpl_str)
        
        ydl_opts = {
            'outtmpl': os.path.join(self.download_dir, outtmpl_str),
            'format': fmt_str,
            'logger': YTSageLoggerInterceptor(self.url, self.signals),
            'progress_hooks': [self._progress_hook],
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 15,
            'retries': 3,
            'overwrites': True,
            'ignoreerrors': True,
            
            # HIZ OPTİMİZASYONLARI
            'concurrent_fragment_downloads': 6,
            'http_chunk_size': 10485760,
            'extractor_args': {'youtube': ['player_client=web,android_tv']},
        }
        
        limit_kbps = self.config.get("speed_limit_kbps")
        if limit_kbps > 0:
            ydl_opts['ratelimit'] = limit_kbps * 1024
            
        proxy = self.config.get("proxy")
        if proxy:
            ydl_opts['proxy'] = proxy

        if self.config.get("create_nfo"):
            ydl_opts['writeinfojson'] = True
            
        if self.config.get("download_thumbnail"):
            ydl_opts['writethumbnail'] = True
            
        browser_cookies = self.config.get("browser_cookies")
        if browser_cookies:
            ydl_opts['cookiesfrombrowser'] = [browser_cookies.lower()]
            
        if self.config.get("download_subs"):
            ydl_opts['writesubtitles'] = True
            ydl_opts['writeautomaticsub'] = True
            ydl_opts['subtitleslangs'] = ['all']
            ydl_opts['subtitlesformat'] = 'srt/best'

        if self.format_quality == "Audio (MP3)":
            mp3_q = str(self.config.get("mp3_quality"))
            if not mp3_q: mp3_q = "192"
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': mp3_q,
            }]
        else:
            ydl_opts['merge_output_format'] = 'mkv'

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=True)
                final_path = ydl.prepare_filename(info)
                if self.format_quality == "Audio (MP3)":
                    final_path = os.path.splitext(final_path)[0] + '.mp3'
                    
                # NFO Converter & Hayalet Dosya Temizleyicisi (Hack #2)
                if self.config.get("create_nfo") and not self._is_cancelled:
                    base_path = os.path.splitext(final_path)[0]
                    info_json_path = base_path + '.info.json'
                    if os.path.exists(info_json_path):
                        try:
                            with open(info_json_path, 'r', encoding='utf-8') as jf:
                                jdata = json.load(jf)
                            root = ET.Element("movie")
                            ET.SubElement(root, "title").text = str(jdata.get("title", ""))
                            ET.SubElement(root, "originaltitle").text = str(jdata.get("fulltitle", ""))
                            ET.SubElement(root, "plot").text = str(jdata.get("description", ""))
                            ET.SubElement(root, "studio").text = str(jdata.get("extractor_key", ""))
                            ET.SubElement(root, "premiered").text = str(jdata.get("upload_date", ""))
                            ET.SubElement(root, "durationinseconds").text = str(jdata.get("duration", "0"))
                            tree = ET.ElementTree(root)
                            tree.write(base_path + '.nfo', encoding='utf-8', xml_declaration=True)
                        except Exception as e:
                            print(f"NFO Hatası: {e}")
                        finally:
                            # İşlem çökse bile bu blok mutlaka çalışacak ve çöp dosyayı silecektir
                            try:
                                if os.path.exists(info_json_path):
                                    os.remove(info_json_path)
                            except Exception:
                                pass

                if not self._is_cancelled:
                    self.signals.download_finished.emit(self.url, final_path)
        except yt_dlp.utils.DownloadCancelled:
            self.signals.download_error.emit(self.url, "İptal Edildi")
        except Exception as e:
            if "KullaniciIptalIstegi" not in str(e):
                self.signals.download_error.emit(self.url, str(e))