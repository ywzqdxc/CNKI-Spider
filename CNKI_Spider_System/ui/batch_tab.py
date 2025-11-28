import customtkinter as ctk
from tkinter import messagebox, filedialog
import threading
import os


class BatchTab(ctk.CTkFrame):
    """批量处理选项卡"""

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
        self.setup_ui()

    def setup_ui(self):
        """设置UI界面"""
        # 主标题
        title_label = ctk.CTkLabel(
            self,
            text="批量链接处理",
            font=("Arial", 20, "bold")
        )
        title_label.pack(pady=20)

        # 文件选择框架
        file_frame = ctk.CTkFrame(self)
        file_frame.pack(pady=10, padx=20, fill="x")

        ctk.CTkLabel(file_frame, text="链接文件:", font=("Arial", 14)).grid(
            row=0, column=0, padx=10, pady=10, sticky="w"
        )

        self.file_path_var = ctk.StringVar()
        self.file_entry = ctk.CTkEntry(
            file_frame,
            textvariable=self.file_path_var,
            width=400,
            font=("Arial", 12)
        )
        self.file_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.browse_button = ctk.CTkButton(
            file_frame,
            text="浏览",
            command=self.browse_file,
            width=80,
            font=("Arial", 12)
        )
        self.browse_button.grid(row=0, column=2, padx=10, pady=10)

        # 处理选项框架
        option_frame = ctk.CTkFrame(self)
        option_frame.pack(pady=10, padx=20, fill="x")

        ctk.CTkLabel(option_frame, text="批量大小:", font=("Arial", 14)).grid(
            row=0, column=0, padx=10, pady=10, sticky="w"
        )

        self.batch_size_var = ctk.StringVar(value="30")
        batch_combo = ctk.CTkComboBox(
            option_frame,
            values=["10", "20", "30", "50", "100"],
            variable=self.batch_size_var,
            width=100,
            font=("Arial", 12)
        )
        batch_combo.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        # 按钮框架
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(pady=20)

        self.process_button = ctk.CTkButton(
            button_frame,
            text="开始处理",
            command=self.start_processing,
            font=("Arial", 14, "bold"),
            width=120,
            height=40
        )
        self.process_button.pack(side="left", padx=10)

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

        # 进度框架
        progress_frame = ctk.CTkFrame(self)
        progress_frame.pack(pady=10, padx=20, fill="x")

        ctk.CTkLabel(progress_frame, text="处理进度:", font=("Arial", 14)).pack(anchor="w", pady=10)

        self.progress_bar = ctk.CTkProgressBar(progress_frame, width=400)
        self.progress_bar.pack(pady=10, padx=10, fill="x")
        self.progress_bar.set(0)

        # 结果框架
        result_frame = ctk.CTkFrame(self)
        result_frame.pack(pady=10, padx=20, fill="both", expand=True)

        ctk.CTkLabel(result_frame, text="处理结果:", font=("Arial", 16, "bold")).pack(anchor="w", pady=10)

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
        self.current_links = []

    def browse_file(self):
        """浏览文件"""
        filename = filedialog.askopenfilename(
            title="选择链接文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if filename:
            self.file_path_var.set(filename)

    def start_processing(self):
        """开始处理"""
        file_path = self.file_path_var.get()
        if not file_path or not os.path.exists(file_path):
            messagebox.showerror("错误", "请选择有效的链接文件")
            return

        # 读取链接
        from utils.file_manager import FileManager
        links = FileManager.load_links(file_path)
        if not links:
            messagebox.showerror("错误", "链接文件为空或格式错误")
            return

        self.current_links = links

        # 禁用按钮
        self.process_button.configure(state="disabled")
        self.export_button.configure(state="disabled")
        self.visualize_button.configure(state="disabled")
        self.status_label.configure(text="处理中...")
        self.progress_bar.set(0)

        # 在新线程中执行处理
        thread = threading.Thread(
            target=self._process_thread,
            args=(links,)
        )
        thread.daemon = True
        thread.start()

    def _process_thread(self, links: list):
        """处理线程"""
        try:
            batch_size = int(self.batch_size_var.get())
            total_links = len(links)
            results = []

            for i in range(0, total_links, batch_size):
                batch_links = links[i:i + batch_size]
                batch_results = self.spider.process_existing_links(batch_links)
                results.extend(batch_results)

                # 更新进度
                progress = min((i + len(batch_links)) / total_links, 1.0)
                self.after(0, self._update_progress, progress, f"已处理 {len(results)}/{total_links}")

            self.current_results = results

            # 更新UI
            self.after(0, self._update_results, results)

        except Exception as e:
            self.after(0, self._show_error, str(e))

    def _update_progress(self, progress: float, message: str):
        """更新进度"""
        self.progress_bar.set(progress)
        self.status_label.configure(text=message)

    def _update_results(self, results):
        """更新结果"""
        self.result_text.delete("1.0", "end")

        if not results:
            self.result_text.insert("end", "处理完成，但未获取到有效数据")
        else:
            success_count = len(results)
            self.result_text.insert("end", f"处理完成！成功获取 {success_count} 篇文献摘要\n\n")

            for i, paper in enumerate(results[:10], 1):  # 只显示前10条
                self.result_text.insert("end", f"{i}. {paper.get('title', '未知标题')}\n")

                abstract = paper.get('abstract', '')
                if len(abstract) > 80:
                    abstract = abstract[:80] + "..."
                self.result_text.insert("end", f"   摘要: {abstract}\n")
                self.result_text.insert("end", "-" * 60 + "\n")

            if len(results) > 10:
                self.result_text.insert("end", f"... 还有 {len(results) - 10} 条记录未显示\n")

        self.status_label.configure(text=f"处理完成，成功 {len(results)} 篇")
        self.process_button.configure(state="normal")
        self.export_button.configure(state="normal")
        self.visualize_button.configure(state="normal")

    def _show_error(self, error_msg):
        """显示错误"""
        messagebox.showerror("错误", f"处理失败: {error_msg}")
        self.status_label.configure(text="处理失败")
        self.process_button.configure(state="normal")

    def export_data(self):
        """导出数据"""
        if not self.current_results:
            messagebox.showwarning("警告", "没有数据可导出")
            return

        # 使用文件名作为基础名称
        base_name = os.path.splitext(os.path.basename(self.file_path_var.get()))[0]

        from utils.data_exporter import DataExporter

        DataExporter.export_to_csv(
            self.current_results,
            f"data/processed/{base_name}.csv"
        )
        DataExporter.export_to_json(
            self.current_results,
            f"data/processed/{base_name}.json"
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

        base_name = os.path.splitext(os.path.basename(self.file_path_var.get()))[0]

        self.visualizer.create_comprehensive_dashboard(
            self.current_results,
            f"data/processed/{base_name}_dashboard.png"
        )