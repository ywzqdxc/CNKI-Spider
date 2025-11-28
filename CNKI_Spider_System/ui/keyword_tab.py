import customtkinter as ctk
from tkinter import messagebox
import threading
import os


class KeywordTab(ctk.CTkFrame):
    """关键词检索选项卡"""

    def __init__(self, master, config):
        super().__init__(master)
        self.config = config

        # 导入必要的模块
        from core.unified_spider import UnifiedSpider
        from utils.data_exporter import DataExporter
        from utils.visualizer import DataVisualizer

        self.spider = UnifiedSpider(
            config.get('chrome_driver_path'),
            config.get('headless', False)
        )
        self.visualizer = DataVisualizer()
        self.setup_ui()

    def setup_ui(self):
        """设置UI界面"""
        # 主标题
        title_label = ctk.CTkLabel(
            self,
            text="关键词文献检索",
            font=("Arial", 20, "bold")
        )
        title_label.pack(pady=20)

        # 输入框架
        input_frame = ctk.CTkFrame(self)
        input_frame.pack(pady=10, padx=20, fill="x")

        # 关键词输入
        ctk.CTkLabel(input_frame, text="关键词:", font=("Arial", 14)).grid(
            row=0, column=0, padx=10, pady=10, sticky="w"
        )
        self.keyword_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="请输入检索关键词...",
            width=300,
            font=("Arial", 12)
        )
        self.keyword_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        # 数量选择
        ctk.CTkLabel(input_frame, text="检索数量:", font=("Arial", 14)).grid(
            row=1, column=0, padx=10, pady=10, sticky="w"
        )
        self.count_var = ctk.StringVar(value="20")
        count_combo = ctk.CTkComboBox(
            input_frame,
            values=["10", "20", "50", "100"],
            variable=self.count_var,
            width=150,
            font=("Arial", 12)
        )
        count_combo.grid(row=1, column=1, padx=10, pady=10, sticky="w")

        # 按钮框架
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(pady=20)

        self.search_button = ctk.CTkButton(
            button_frame,
            text="开始检索",
            command=self.start_search,
            font=("Arial", 14, "bold"),
            width=120,
            height=40
        )
        self.search_button.pack(side="left", padx=10)

        self.export_button = ctk.CTkButton(
            button_frame,
            text="导出数据",
            command=self.export_data,
            font=("Arial", 14),
            width=120,
            height=40,
            state="disabled"
        )
        self.export_button.pack(side="left", padx=10)

        self.visualize_button = ctk.CTkButton(
            button_frame,
            text="数据可视化",
            command=self.visualize_data,
            font=("Arial", 14),
            width=120,
            height=40,
            state="disabled"
        )
        self.visualize_button.pack(side="left", padx=10)

        # 结果框架
        result_frame = ctk.CTkFrame(self)
        result_frame.pack(pady=10, padx=20, fill="both", expand=True)

        # 结果文本框
        ctk.CTkLabel(result_frame, text="检索结果:", font=("Arial", 16, "bold")).pack(anchor="w", pady=10)

        self.result_text = ctk.CTkTextbox(
            result_frame,
            width=800,
            height=300,
            font=("Arial", 11)
        )
        self.result_text.pack(pady=10, padx=10, fill="both", expand=True)

        # 状态标签
        self.status_label = ctk.CTkLabel(self, text="就绪", font=("Arial", 12))
        self.status_label.pack(pady=10)

        self.current_results = []

    def start_search(self):
        """开始检索"""
        keyword = self.keyword_entry.get().strip()
        if not keyword:
            messagebox.showerror("错误", "请输入关键词")
            return

        count = int(self.count_var.get())

        # 禁用按钮
        self.search_button.configure(state="disabled")
        self.export_button.configure(state="disabled")
        self.visualize_button.configure(state="disabled")
        self.status_label.configure(text="检索中...")

        # 在新线程中执行检索
        thread = threading.Thread(
            target=self._search_thread,
            args=(keyword, count)
        )
        thread.daemon = True
        thread.start()

    def _search_thread(self, keyword: str, count: int):
        """检索线程"""
        try:
            results = self.spider.search_by_keyword(keyword, count)
            self.current_results = results

            # 更新UI
            self.after(0, self._update_results, results)

        except Exception as e:
            self.after(0, self._show_error, str(e))

    def _update_results(self, results):
        """更新结果"""
        # 清空结果文本框
        self.result_text.delete("1.0", "end")

        if not results:
            self.result_text.insert("end", "未找到相关文献")
        else:
            for i, paper in enumerate(results, 1):
                self.result_text.insert("end", f"{i}. {paper.get('title', '未知标题')}\n")
                self.result_text.insert("end", f"   年份: {paper.get('year', '未知')}\n")

                abstract = paper.get('abstract', '')
                if len(abstract) > 100:
                    abstract = abstract[:100] + "..."
                self.result_text.insert("end", f"   摘要: {abstract}\n")
                self.result_text.insert("end", f"   链接: {paper.get('link', '')}\n")
                self.result_text.insert("end", "-" * 80 + "\n")

        # 更新状态和按钮
        self.status_label.configure(text=f"检索完成，找到 {len(results)} 篇文献")
        self.search_button.configure(state="normal")
        self.export_button.configure(state="normal")
        self.visualize_button.configure(state="normal")

    def _show_error(self, error_msg):
        """显示错误"""
        messagebox.showerror("错误", f"检索失败: {error_msg}")
        self.status_label.configure(text="检索失败")
        self.search_button.configure(state="normal")

    def export_data(self):
        """导出数据"""
        if not self.current_results:
            messagebox.showwarning("警告", "没有数据可导出")
            return

        # 这里可以添加文件选择对话框
        base_name = f"keyword_{self.keyword_entry.get().strip()}"

        # 导出各种格式
        from utils.data_exporter import DataExporter

        DataExporter.export_to_csv(
            self.current_results,
            f"data/keyword/{base_name}.csv"
        )
        DataExporter.export_to_json(
            self.current_results,
            f"data/keyword/{base_name}.json"
        )
        DataExporter.export_to_jsonl(
            self.current_results,
            f"data/processed/{base_name}.jsonl"
        )

        messagebox.showinfo("成功", "数据导出完成")

    def visualize_data(self):
        """数据可视化"""
        if not self.current_results:
            messagebox.showwarning("警告", "没有数据可可视化")
            return

        base_name = f"keyword_{self.keyword_entry.get().strip()}"

        # 创建综合仪表板
        self.visualizer.create_comprehensive_dashboard(
            self.current_results,
            f"data/keyword/{base_name}_dashboard.png"
        )