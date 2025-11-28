#!/usr/bin/env python3
"""
知网文献数据采集系统 - 主程序入口
"""

import sys
import os
import logging

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import MainWindow
from utils.file_manager import FileManager


def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/app.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )


def check_dependencies():
    """检查依赖"""
    try:
        import customtkinter
        import selenium
        import pandas
        return True
    except ImportError as e:
        print(f"缺少依赖包: {e}")
        print("请运行: pip install -r requirements.txt")
        return False


def main():
    """主函数"""
    print("启动知网文献数据采集系统...")

    # 检查依赖
    if not check_dependencies():
        return

    # 设置日志
    setup_logging()

    # 确保目录存在
    FileManager.ensure_directory("data/keyword")
    FileManager.ensure_directory("data/journal")
    FileManager.ensure_directory("data/processed")
    FileManager.ensure_directory("links")
    FileManager.ensure_directory("logs")

    # 创建并运行应用
    try:
        app = MainWindow()
        app.run()
    except Exception as e:
        logging.error(f"应用程序错误: {e}")
        print(f"应用程序错误: {e}")


if __name__ == "__main__":
    main()