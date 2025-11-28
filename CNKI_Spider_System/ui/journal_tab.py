import customtkinter as ctk
from tkinter import messagebox
import threading
import json
import os


class JournalTab(ctk.CTkFrame):
    """期刊检索选项卡"""

    def __init__(self, master, config):
        super().__init__(master)
        self.config = config

        # 导入必要的模块
        from core.unified_spider import UnifiedSpider
        from utils.data_exporter import DataExporter
        from utils.file_manager import FileManager
        from utils.visualizer import DataVisualizer

        self.spider = UnifiedSpider(
            config.get('chrome_driver_path'),
            config.get('headless', False)
        )
        self.visualizer = DataVisualizer()
        self.common_issn = self.load_common_issn()
        self.setup_ui()

    def load_common_issn(self):
        """加载常用ISSN号"""
        try:
            with open("data/common_issn.json", 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}

    def setup_ui(self):
        """设置UI界面"""
        # 主标题
        title_label = ctk.CTkLabel(
            self,
            text="期刊文献检索",
            font=("Arial", 20, "bold")
        )
        title_label.pack(pady=20)

        # 输入框架
        input_frame = ctk.CTkFrame(self)
        input_frame.pack(pady=10, padx=20, fill="x")

        # ISSN选择框架
        issn_frame = ctk.CTkFrame(input_frame)
        issn_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(issn_frame, text="ISSN号:", font=("Arial", 14)).pack(side="left", padx=10)

        # 常用期刊选择
        self.issn_var = ctk.StringVar()
        self.issn_combo = ctk.CTkComboBox(
            issn_frame,
            values=self.get_issn_list(),
            variable=self.issn_var,
            width=300,
            font=("Arial", 12),
            command=self.on_issn_selected
        )
        self.issn_combo.pack(side="left", padx=10, fill="x", expand=True)

        # 自定义ISSN输入
        ctk.CTkLabel(issn_frame, text="或自定义:", font=("Arial", 12)).pack(side="left", padx=10)
        self.custom_issn_entry = ctk.CTkEntry(
            issn_frame,
            placeholder_text="输入ISSN号...",
            width=150,
            font=("Arial", 12)
        )
        self.custom_issn_entry.pack(side="left", padx=10)

        # 年份范围
        year_frame = ctk.CTkFrame(input_frame)
        year_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(year_frame, text="年份范围:", font=("Arial", 14)).pack(side="left", padx=10)

        self.start_year_var = ctk.StringVar(value="2020")
        self.start_year_combo = ctk.CTkComboBox(
            year_frame,
            values=[str(year) for year in range(2010, 2025)],
            variable=self.start_year_var,
            width=100,
            font=("Arial", 12)
        )
        self.start_year_combo.pack(side="left", padx=5)

        ctk.CTkLabel(year_frame, text="至", font=("Arial", 14)).pack(side="left", padx=5)

        self.end_year_var = ctk.StringVar(value="2024")
        self.end_year_combo = ctk.CTkComboBox(
            year_frame,
            values=[str(year) for year in range(2010, 2025)],
            variable=self.end_year_var,
            width=100,
            font=("Arial", 12)
        )
        self.end_year_combo.pack(side="left", padx=5)

        # 检索数量
        count_frame = ctk.CTkFrame(input_frame)
        count_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(count_frame, text="检索数量:", font=("Arial", 14)).pack(side="left", padx=10)

        self.count_var = ctk.StringVar(value="30")
        self.count_combo = ctk.CTkComboBox(
            count_frame,
            values=["10", "20", "30", "50", "100"],
            variable=self.count_var,
            width=100,
            font=("Arial", 12)
        )
        self.count_combo.pack(side="left", padx=10)

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

    def get_issn_list(self):
        """获取ISSN列表"""
        issn_list = []
        for category, journals in self.common_issn.items():
            for journal, issn in journals.items():
                issn_list.append(f"{journal} ({issn})")
        return issn_list

    def on_issn_selected(self, choice):
        """ISSN选择事件"""
        if choice:
            # 从选择中提取ISSN号
            issn = choice.split('(')[-1].rstrip(')')
            self.custom_issn_entry.delete(0, "end")
            self.custom_issn_entry.insert(0, issn)

    def start_search(self):
        """开始检索"""
        issn = self.custom_issn_entry.get().strip()
        if not issn:
            messagebox.showerror("错误", "请输入ISSN号")
            return

        try:
            start_year = int(self.start_year_var.get())
            end_year = int(self.end_year_var.get())
            count = int(self.count_var.get())
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
            return

        if start_year > end_year:
            messagebox.showerror("错误", "起始年份不能大于结束年份")
            return

        # 禁用按钮
        self.search_button.configure(state="disabled")
        self.export_button.configure(state="disabled")
        self.visualize_button.configure(state="disabled")
        self.status_label.configure(text="检索中...")

        # 在新线程中执行检索
        thread = threading.Thread(
            target=self._search_thread,
            args=(issn, [start_year, end_year], count)
        )
        thread.daemon = True
        thread.start()

    def _search_thread(self, issn: str, year_range: list, count: int):
        """检索线程"""
        try:
            results = self.spider.search_by_issn(issn, year_range, count)
            self.current_results = results

            # 更新UI
            self.after(0, self._update_results, results)

        except Exception as e:
            self.after(0, self._show_error, str(e))

    def _update_results(self, results):
        """更新结果"""
        self.result_text.delete("1.0", "end")

        if not results:
            self.result_text.insert("end", "未找到相关文献")
        else:
            for i, paper in enumerate(results, 1):
                self.result_text.insert("end", f"{i}. {paper.get('title', '未知标题')}\n")

                abstract = paper.get('abstract', '')
                if len(abstract) > 100:
                    abstract = abstract[:100] + "..."
                self.result_text.insert("end", f"   摘要: {abstract}\n")
                self.result_text.insert("end", f"   链接: {paper.get('link', '')}\n")
                self.result_text.insert("end", "-" * 80 + "\n")

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

        issn = self.custom_issn_entry.get().strip()
        base_name = f"journal_{issn}"

        from utils.data_exporter import DataExporter

        DataExporter.export_to_csv(
            self.current_results,
            f"data/journal/{base_name}.csv"
        )
        DataExporter.export_to_json(
            self.current_results,
            f"data/journal/{base_name}.json"
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

        issn = self.custom_issn_entry.get().strip()
        base_name = f"journal_{issn}"

        self.visualizer.create_comprehensive_dashboard(
            self.current_results,
            f"data/journal/{base_name}_dashboard.png"
        )