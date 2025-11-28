import json
import os

class ConfigLoader:
    """配置加载器"""

    def __init__(self, config_path: str = "config/settings.json"):
        self.config_path = config_path
        self.config = self.load_config()

    def load_config(self) -> dict:
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # 返回默认配置
            return {
                "chrome_driver_path": "C:/Program Files/Google/Chrome/Application/chromedriver.exe",
                "chrome_binary_path": "C:/Program Files/Google/Chrome/Application/chrome.exe",
                "max_workers": 2,
                "batch_size": 30,
                "max_retries": 3,
                "headless": False,
                "debug": True,
                "data_dir": "data",
                "link_dir": "links",
                "save_dir": "saves"
            }

    def get(self, key: str, default=None):
        """获取配置值"""
        return self.config.get(key, default)

    def load_common_issn(self) -> dict:
        """加载常用ISSN号"""
        try:
            with open("data/common_issn.json", 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}