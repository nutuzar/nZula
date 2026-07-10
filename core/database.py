import sqlite3
import os
import json

class DatabaseManager:
    def __init__(self, db_path="ndownloader_history.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(downloads)")
            columns = cursor.fetchall()
            if columns:
                cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='downloads'")
                create_stmt = cursor.fetchone()[0]
                if "UNIQUE(url, file_path)" not in create_stmt.replace(" ", "") and "UNIQUE(url,file_path)" not in create_stmt.replace(" ", ""):
                    cursor.execute("ALTER TABLE downloads RENAME TO downloads_old")
                    cursor.execute('''
                        CREATE TABLE downloads (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            url TEXT,
                            title TEXT,
                            file_path TEXT,
                            status TEXT,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(url, file_path)
                        )
                    ''')
                    cursor.execute('''
                        INSERT OR IGNORE INTO downloads (url, title, file_path, status, timestamp)
                        SELECT url, title, file_path, status, timestamp FROM downloads_old
                    ''')
                    cursor.execute("DROP TABLE downloads_old")
            else:
                cursor.execute('''
                    CREATE TABLE downloads (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url TEXT,
                        title TEXT,
                        file_path TEXT,
                        status TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(url, file_path)
                    )
                ''')
            conn.commit()

    def save_download(self, url: str, title: str, file_path: str, status: str = "completed"):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO downloads (url, title, file_path, status)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(url, file_path) DO UPDATE SET 
                        title=excluded.title,
                        status=excluded.status,
                        timestamp=CURRENT_TIMESTAMP
                ''', (url, title, file_path, status))
                conn.commit()
        except Exception as e:
            pass

    def get_history(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT url, title, file_path, status, timestamp FROM downloads ORDER BY timestamp DESC')
                return cursor.fetchall()
        except Exception as e:
            return []

    def clear_history(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM downloads')
                conn.commit()
        except Exception:
            pass

    def get_total_stats(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT file_path FROM downloads WHERE status="completed"')
                rows = cursor.fetchall()
                total_bytes = 0
                valid_files = 0
                for r in rows:
                    if r[0] and os.path.exists(r[0]):
                        total_bytes += os.path.getsize(r[0])
                        valid_files += 1
                return valid_files, total_bytes / (1024 * 1024 * 1024)
        except Exception:
            return 0, 0.0
