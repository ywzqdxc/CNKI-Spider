import sys
import os

# === 1. 最优先导入 PyQt5 核心 ===
# 这是解决 'QFontDatabase' 和 'qt_material' 警告的关键
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import Qt

# === 2. 其次导入项目代码 ===
# 确保在 import main_window 之前，QApplication 相关的环境已经准备好
from src.main_window import MainWindow

# === 3. 最后导入主题库 ===
# 如果没有安装，做一个假的 apply_stylesheet 防止报错
try:
    from qt_material import apply_stylesheet
except ImportError:
    apply_stylesheet = None
    print("注意: 未安装 qt_material，将使用默认界面。")


def main():
    # 解决高分屏显示模糊的问题
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # 创建应用实例
    app = QApplication(sys.argv)

    # 创建主窗口
    window = MainWindow()

    # 应用主题 (建议使用 dark_teal.xml)
    if apply_stylesheet:
        try:
            # invert_secondary=True 可以解决部分按钮文字看不清的问题
            apply_stylesheet(app, theme='dark_teal.xml', invert_secondary=True)
        except Exception as e:
            print(f"应用主题失败 (可能是 qt_material 版本兼容性问题): {e}")

    window.show()

    # 进入事件循环
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()