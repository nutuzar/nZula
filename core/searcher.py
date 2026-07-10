import random
import urllib.parse
import re
import requests
from typing import List, Dict, Any, Optional
from PySide6.QtCore import QThread, Signal, QObject, QMutex, QMutexLocker
from loguru import logger
import yt_dlp

class SearchSignals(QObject):
    search_started = Signal(str)
    result_found = Signal(dict)
    search_completed = Signal(list)
    search_error = Signal(str)
    playlist_detected = Signal(str, int, str)

class MetadataFetchSignals(QObject):
    metadata_fetched = Signal(str, dict)
    fetch_completed = Signal()

class MetadataFetchWorker(QThread):
    def __init__(self, urls: List[str], parent: Optional[QObject] = None):
        super().__init__(parent)
        self.urls = urls
        self.signals = MetadataFetchSignals()
        self._is_cancelled = False
        self._mutex = QMutex()
        
    def cancel(self) -> None:
        with QMutexLocker(self._mutex):
            self._is_cancelled = True
            
    def _check_cancellation(self) -> bool:
        with QMutexLocker(self._mutex):
            return self._is_cancelled
            
    def _fetch_single(self, url: str) -> None:
        ydl_opts = {
            'quiet': True, 'no_warnings': True, 'extract_flat': False, 'skip_download': True, 'socket_timeout': 8
        }
        from core.config import ConfigManager
        cfg = ConfigManager()
        browser_cookies = cfg.get("browser_cookies")
        if browser_cookies:
            ydl_opts['cookiesfrombrowser'] = [browser_cookies.lower()]
            
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                if not info: return
                
                size = info.get('filesize') or info.get('filesize_approx')
                if size:
                    if size > 1024*1024*1024: filesize_str = f"{size/(1024*1024*1024):.2f} GB"
                    else: filesize_str = f"{size/(1024*1024):.1f} MB"
                else:
                    filesize_str = "?"
                    
                resolutions = []
                if 'formats' in info:
                    for f in info['formats']:
                        h = f.get('height')
                        if h and h >= 144: resolutions.append(h)
                    resolutions = sorted(list(set(resolutions)), reverse=True)
                    res_strs = [f"{h}p" for h in resolutions]
                else:
                    res_strs = []
                    
                duration_raw = info.get('duration', 0)
                try:
                    sec = int(duration_raw)
                    mins, secs = divmod(sec, 60)
                    hours, mins = divmod(mins, 60)
                    duration_str = f"{hours:02d}:{mins:02d}:{secs:02d}" if hours else f"{mins:02d}:{secs:02d}"
                except:
                    duration_str = "00:00"
                    
                new_meta = {
                    'filesize': filesize_str,
                    'resolutions': res_strs,
                    'duration': duration_str
                }
                self.signals.metadata_fetched.emit(url, new_meta)
            except Exception as e:
                logger.error(f"Metadata fetch hatası ({url}): {e}")

    def run(self) -> None:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for url in self.urls:
                if self._check_cancellation(): break
                futures.append(executor.submit(self._fetch_single, url))
            
            for future in concurrent.futures.as_completed(futures):
                if self._check_cancellation(): break
                
        if not self._check_cancellation():
            self.signals.fetch_completed.emit()

class MultiPlatformSearchWorker(QThread):
    def __init__(self, query: str, platforms: List[str], max_results_per_platform: int = 10, min_duration_sec: int = 0, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.query = query.strip()
        self.platforms = [p.lower() for p in platforms]
        self.max_results = max_results_per_platform
        self.min_duration_sec = min_duration_sec
        self.signals = SearchSignals()
        
        self._is_cancelled = False
        self._mutex = QMutex()
        
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ]

    def cancel(self) -> None:
        with QMutexLocker(self._mutex):
            self._is_cancelled = True
        logger.warning(f"Arama motoru durduruluyor: {self.query}")

    def _check_cancellation(self) -> bool:
        with QMutexLocker(self._mutex):
            return self._is_cancelled

    def _get_filesize_str(self, info: dict) -> str:
        size = info.get('filesize') or info.get('filesize_approx')
        if size:
            if size > 1024*1024*1024:
                return f"{size/(1024*1024*1024):.2f} GB"
            return f"{size/(1024*1024):.1f} MB"
        stream_url = info.get('url')
        if stream_url and stream_url.startswith('http'):
            try:
                head = requests.head(stream_url, timeout=2, allow_redirects=True, headers={'User-Agent': self.user_agents[0]})
                cl = head.headers.get('Content-Length')
                if cl and cl.isdigit():
                    size = int(cl)
                    if size > 1024*1024*1024:
                        return f"{size/(1024*1024*1024):.2f} GB"
                    return f"{size/(1024*1024):.1f} MB"
            except:
                pass
        return "?"

    def _process_direct_url(self) -> List[Dict[str, Any]]:
        results = []
        ydl_opts = {
            'quiet': True, 'no_warnings': True, 'extract_flat': 'in_playlist', 'skip_download': True, 'socket_timeout': 8
        }
        
        from core.config import ConfigManager
        cfg = ConfigManager()
        browser_cookies = cfg.get("browser_cookies")
        if browser_cookies:
            ydl_opts['cookiesfrombrowser'] = [browser_cookies.lower()]
            
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.query, download=False)
                if not info: return results
                
                if 'entries' in info:
                    entries = list(info['entries'])
                    self.signals.playlist_detected.emit(info.get('title', 'Oynatma Listesi'), len(entries), self.query)
                    for entry in entries:
                        if self._check_cancellation() or not entry: break
                        url = entry.get('url') or entry.get('webpage_url')
                        if not url: continue
                        meta = self._build_meta(entry, url, "Doğrudan")
                        if meta:
                            results.append(meta)
                            self.signals.result_found.emit(meta)
                    return results
                else:
                    meta = self._build_meta(info, self.query, "Doğrudan")
                    if meta:
                        results.append(meta)
                        self.signals.result_found.emit(meta)
                        
        except Exception as e:
            logger.error(f"Doğrudan URL analizi patladı: {e}")
            
        return results

    def _build_meta(self, info: dict, url: str, default_platform: str) -> Optional[Dict[str, Any]]:
        duration_raw = info.get('duration', 0)
        try:
            sec = int(duration_raw)
            mins, secs = divmod(sec, 60)
            hours, mins = divmod(mins, 60)
            duration_str = f"{hours:02d}:{mins:02d}:{secs:02d}" if hours else f"{mins:02d}:{secs:02d}"
        except:
            sec = 0
            duration_str = "Medya"
            
        if self.min_duration_sec > 0 and sec < self.min_duration_sec:
            return None

        display_platform = default_platform
        lower_url = url.lower()
        if "youtube.com" in lower_url or "youtu.be" in lower_url: display_platform = "YouTube"
        elif "ok.ru" in lower_url: display_platform = "ok.ru"
        elif "vk.com" in lower_url: display_platform = "VK"
        elif "mail.ru" in lower_url: display_platform = "Mail.ru"
        elif "rutube.ru" in lower_url: display_platform = "RuTube"
        elif "archive.org" in lower_url: display_platform = "Archive.org"
        elif "bilibili" in lower_url: display_platform = "Bilibili"

        thumbnail_url = info.get('thumbnail', '')
        if display_platform == "YouTube" and info.get('id'):
            thumbnail_url = f"https://img.youtube.com/vi/{info.get('id')}/mqdefault.jpg"

        filesize_str = self._get_filesize_str(info)

        resolutions = []
        if 'formats' in info:
            for f in info['formats']:
                h = f.get('height')
                if h and h >= 144:
                    resolutions.append(h)
            resolutions = sorted(list(set(resolutions)), reverse=True)
            res_strs = [f"{h}p" for h in resolutions]
        else:
            res_strs = []

        return {
            'url': url,
            'title': info.get('title', f'{display_platform} Dosyası'),
            'duration': duration_str,
            'thumbnail': thumbnail_url,
            'uploader': info.get('uploader', 'Arşivci'),
            'platform': display_platform,
            'filesize': filesize_str,
            'resolutions': res_strs
        }

    def _search_youtube_native(self) -> List[Dict[str, Any]]:
        results = []
        search_query = f"ytsearch{self.max_results}:{self.query}"
        ydl_opts = {
            'quiet': True, 'no_warnings': True, 'extract_flat': True, 'skip_download': True, 'socket_timeout': 5,
            'http_headers': {'User-Agent': self.user_agents[0]}
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=False)
                if not info or 'entries' not in info: return results
                for entry in info['entries']:
                    if self._check_cancellation() or not entry: break
                    video_id = entry.get('id')
                    url = f"https://www.youtube.com/watch?v={video_id}"
                    meta = self._build_meta(entry, url, 'YouTube')
                    if meta:
                        results.append(meta)
                        self.signals.result_found.emit(meta)
        except Exception as e:
            logger.error(f"YouTube hatası: {e}")
        return results

    def _search_archive_org_native(self) -> List[Dict[str, Any]]:
        results = []
        url = "https://archive.org/advancedsearch.php"
        params = {'q': f'title:({self.query}) AND mediatype:(movies) AND format:("h.264" OR "Matroska" OR "MPEG4")', 'fl[]': 'identifier,title,uploader,length', 'sort[]': 'downloads desc', 'rows': self.max_results, 'output': 'json'}
        try:
            response = requests.get(url, params=params, timeout=8)
            if response.status_code == 200:
                docs = response.json().get('response', {}).get('docs', [])
                for doc in docs:
                    if self._check_cancellation(): break
                    id_ = doc.get('identifier')
                    meta = self._build_meta({
                        'duration': doc.get('length', 0),
                        'title': doc.get('title', 'Archive.org Medyası'),
                        'thumbnail': f"https://archive.org/services/img/{id_}",
                        'uploader': doc.get('uploader', 'Kamu Arşivi')
                    }, f"https://archive.org/details/{id_}", 'Archive.org')
                    if meta:
                        meta['filesize'] = "?"
                        results.append(meta)
                        self.signals.result_found.emit(meta)
        except Exception as e:
            logger.error(f"Archive.org hatası: {e}")
        return results

    def run(self) -> None:
        self.signals.search_started.emit(self.query)
        if self.query.startswith("http://") or self.query.startswith("https://"):
            direct_res = self._process_direct_url()
            self.signals.search_completed.emit(direct_res)
            return

        total_results = []
        import concurrent.futures
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                futures = []
                if "youtube" in self.platforms and not self._check_cancellation(): futures.append(executor.submit(self._search_youtube_native))
                if "archive.org" in self.platforms and not self._check_cancellation(): futures.append(executor.submit(self._search_archive_org_native))

                for future in concurrent.futures.as_completed(futures):
                    if self._check_cancellation(): break
                    try:
                        res = future.result()
                        if res: total_results.extend(res)
                    except Exception: pass

            if not self._check_cancellation():
                self.signals.search_completed.emit(total_results)
        except Exception as e:
            self.signals.search_error.emit(str(e))