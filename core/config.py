import json
import os
from typing import Any, Dict

class ConfigManager:
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.default_config = {
            "max_concurrent_downloads": 2,
            "speed_limit_kbps": 0,  # 0 means unlimited
            "auto_shutdown": False,
            "naming_template": "%(title)s - %(extractor)s.%(ext)s",
            "auto_subfolder_by_platform": False,
            "create_nfo": False,
            "download_thumbnail": False,
            "proxy": "",
            "download_subs": False,
            "browser_cookies": "",
            "mp3_quality": "192",
            "lang": "tr",
            "download_dir": os.path.join(os.path.expanduser("~"), "Downloads", "nZula")
        }
        self.config = self.load()

    def load(self) -> Dict[str, Any]:
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    user_cfg = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    for k, v in self.default_config.items():
                        if k not in user_cfg:
                            user_cfg[k] = v
                    return user_cfg
            except Exception:
                pass
        return self.default_config.copy()

    def save(self) -> None:
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Config kaydetme hatası: {e}")

    def get(self, key: str) -> Any:
        return self.config.get(key, self.default_config.get(key))

    def set(self, key: str, value: Any) -> None:
        self.config[key] = value
        self.save()
