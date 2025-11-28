import os
import json
from typing import List


class FileManager:
    """文件管理器"""

    @staticmethod
    def ensure_directory(directory: str) -> None:
        """确保目录存在"""
        if not os.path.exists(directory):
            os.makedirs(directory)

    @staticmethod
    def save_links(links: List[str], filename: str) -> None:
        """保存链接到文件"""
        FileManager.ensure_directory(os.path.dirname(filename))

        with open(filename, 'w', encoding='utf-8') as f:
            for link in links:
                f.write(link + '\n')

    @staticmethod
    def load_links(filename: str) -> List[str]:
        """从文件加载链接"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            return []

    @staticmethod
    def get_existing_files(directory: str, extension: str = None) -> List[str]:
        """获取目录中已有的文件"""
        if not os.path.exists(directory):
            return []

        files = []
        for file in os.listdir(directory):
            if extension and not file.endswith(extension):
                continue
            files.append(file)
        return files

    @staticmethod
    def read_jsonl(filename: str) -> List[dict]:
        """读取JSONL文件"""
        data = []
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        data.append(json.loads(line.strip()))
        except FileNotFoundError:
            pass
        return data