import customtkinter as ctk
import os


class MainWindow:
    """主窗口"""

    def __init__(self):
        # 设置主题
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        # 加载配置
        from utils.config_loader import ConfigLoader
        from utils.file_manager import FileManager

        self.config = ConfigLoader()

        # 创建主窗口
        self.root = ctk.CTk()
        self.root.title("知网文献数据采集系统")
        self.root.geometry("1200x800")

        # 确保必要的目录存在
        self._ensure_directories()

        # 设置UI
        self.setup_ui()

    def _ensure_directories(self):
        """确保必要的目录存在"""
        from utils.file_manager import FileManager

        directories = [
            "data/keyword",
            "data/journal",
            "data/processed",
            "links",
            "config",
            "logs"
        ]

        for directory in directories:
            FileManager.ensure_directory(directory)

    def setup_ui(self):
        """设置UI界面"""
        # 创建主框架
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # 标题
        title_label = ctk.CTkLabel(
            main_frame,
            text="知网文献数据采集系统",
            font=("Arial", 24, "bold")
        )
        title_label.pack(pady=20)

        # 副标题
        subtitle_label = ctk.CTkLabel(
            main_frame,
            text="智能文献检索与数据分析工具",
            font=("Arial", 14),
            text_color="gray"
        )
        subtitle_label.pack(pady=5)

        # 创建选项卡
        self.tabview = ctk.CTkTabview(main_frame)
        self.tabview.pack(pady=20, padx=20, fill="both", expand=True)

        # 添加选项卡
        self.tabview.add("关键词检索")
        self.tabview.add("期刊检索")
        self.tabview.add("批量处理")

        # 创建各个选项卡内容
        from ui.keyword_tab import KeywordTab
        from ui.journal_tab import JournalTab
        from ui.batch_tab import BatchTab

        self.keyword_tab = KeywordTab(self.tabview.tab("关键词检索"), self.config)
        self.keyword_tab.pack(fill="both", expand=True)

        self.journal_tab = JournalTab(self.tabview.tab("期刊检索"), self.config)
        self.journal_tab.pack(fill="both", expand=True)

        self.batch_tab = BatchTab(self.tabview.tab("批量处理"), self.config)
        self.batch_tab.pack(fill="both", expand=True)

        # 状态栏
        status_frame = ctk.CTkFrame(main_frame)
        status_frame.pack(fill="x", padx=20, pady=10)

        status_label = ctk.CTkLabel(
            status_frame,
            text="就绪 | 华北水利水电大学 - 软件工程",
            font=("Arial", 10),
            text_color="gray"
        )
        status_label.pack(side="left", padx=10)

    def run(self):
        """运行应用程序"""
        self.root.mainloop()