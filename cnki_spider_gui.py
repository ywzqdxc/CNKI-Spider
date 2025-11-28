import os
import sys
import time
import json
import logging
import threading
import pandas as pd
from tkinter import messagebox, filedialog
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import customtkinter as ctk

# 设置主题
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class CNKISpiderGUI:
    """知网文献数据采集系统 - 简化版本"""

    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("知网文献数据采集系统")
        self.root.geometry("1000x700")

        # 配置
        self.config = {
            "chrome_driver_path": "C:/Program Files/Google/Chrome/Application/chromedriver.exe",
            "headless": False
        }

        # 确保目录存在
        self.ensure_directories()

        self.setup_ui()

    def ensure_directories(self):
        """确保必要的目录存在"""
        directories = ["data/keyword", "data/journal", "data/processed", "links", "logs"]
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)

    def setup_ui(self):
        """设置UI界面"""
        # 创建选项卡
        self.tabview = ctk.CTkTabview(self.root)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        # 添加选项卡
        self.tabview.add("关键词检索")
        self.tabview.add("期刊检索")
        self.tabview.add("批量处理")

        # 设置各个选项卡
        self.setup_keyword_tab()
        self.setup_journal_tab()
        self.setup_batch_tab()

    def setup_keyword_tab(self):
        """设置关键词检索选项卡"""
        tab = self.tabview.tab("关键词检索")

        # 标题
        title_label = ctk.CTkLabel(tab, text="关键词文献检索", font=("Arial", 20, "bold"))
        title_label.pack(pady=20)

        # 输入框架
        input_frame = ctk.CTkFrame(tab)
        input_frame.pack(pady=10, padx=20, fill="x")

        # 关键词输入
        ctk.CTkLabel(input_frame, text="关键词:", font=("Arial", 14)).grid(row=0, column=0, padx=10, pady=10,
                                                                           sticky="w")
        self.keyword_entry = ctk.CTkEntry(input_frame, placeholder_text="请输入检索关键词...", width=300,
                                          font=("Arial", 12))
        self.keyword_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        # 数量选择
        ctk.CTkLabel(input_frame, text="检索数量:", font=("Arial", 14)).grid(row=1, column=0, padx=10, pady=10,
                                                                             sticky="w")
        self.keyword_count_var = ctk.StringVar(value="20")
        count_combo = ctk.CTkComboBox(input_frame, values=["10", "20", "50", "100"], variable=self.keyword_count_var,
                                      width=150)
        count_combo.grid(row=1, column=1, padx=10, pady=10, sticky="w")

        # 按钮
        button_frame = ctk.CTkFrame(tab)
        button_frame.pack(pady=20)

        self.keyword_search_btn = ctk.CTkButton(button_frame, text="开始检索", command=self.start_keyword_search,
                                                width=120, height=40)
        self.keyword_search_btn.pack(side="left", padx=10)

        self.keyword_export_btn = ctk.CTkButton(button_frame, text="导出数据", command=self.export_keyword_data,
                                                width=120, height=40, state="disabled")
        self.keyword_export_btn.pack(side="left", padx=10)

        # 结果框
        result_frame = ctk.CTkFrame(tab)
        result_frame.pack(pady=10, padx=20, fill="both", expand=True)

        ctk.CTkLabel(result_frame, text="检索结果:", font=("Arial", 16, "bold")).pack(anchor="w", pady=10)

        self.keyword_result_text = ctk.CTkTextbox(result_frame, font=("Arial", 11))
        self.keyword_result_text.pack(pady=10, padx=10, fill="both", expand=True)

        # 状态
        self.keyword_status_label = ctk.CTkLabel(tab, text="就绪")
        self.keyword_status_label.pack(pady=10)

        self.keyword_results = []

    def setup_journal_tab(self):
        """设置期刊检索选项卡"""
        tab = self.tabview.tab("期刊检索")

        # 标题
        title_label = ctk.CTkLabel(tab, text="期刊文献检索", font=("Arial", 20, "bold"))
        title_label.pack(pady=20)

        # 输入框架
        input_frame = ctk.CTkFrame(tab)
        input_frame.pack(pady=10, padx=20, fill="x")

        # ISSN输入
        ctk.CTkLabel(input_frame, text="ISSN号:", font=("Arial", 14)).grid(row=0, column=0, padx=10, pady=10,
                                                                           sticky="w")
        self.issn_entry = ctk.CTkEntry(input_frame, placeholder_text="输入ISSN号...", width=200, font=("Arial", 12))
        self.issn_entry.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        # 年份范围
        ctk.CTkLabel(input_frame, text="年份范围:", font=("Arial", 14)).grid(row=1, column=0, padx=10, pady=10,
                                                                             sticky="w")

        year_frame = ctk.CTkFrame(input_frame)
        year_frame.grid(row=1, column=1, padx=10, pady=10, sticky="w")

        self.start_year_var = ctk.StringVar(value="2020")
        self.start_year_combo = ctk.CTkComboBox(year_frame, values=[str(year) for year in range(2010, 2025)],
                                                variable=self.start_year_var, width=80)
        self.start_year_combo.pack(side="left", padx=5)

        ctk.CTkLabel(year_frame, text="至").pack(side="left", padx=5)

        self.end_year_var = ctk.StringVar(value="2024")
        self.end_year_combo = ctk.CTkComboBox(year_frame, values=[str(year) for year in range(2010, 2025)],
                                              variable=self.end_year_var, width=80)
        self.end_year_combo.pack(side="left", padx=5)

        # 数量选择
        ctk.CTkLabel(input_frame, text="检索数量:", font=("Arial", 14)).grid(row=2, column=0, padx=10, pady=10,
                                                                             sticky="w")
        self.journal_count_var = ctk.StringVar(value="30")
        count_combo = ctk.CTkComboBox(input_frame, values=["10", "20", "30", "50", "100"],
                                      variable=self.journal_count_var, width=150)
        count_combo.grid(row=2, column=1, padx=10, pady=10, sticky="w")

        # 按钮
        button_frame = ctk.CTkFrame(tab)
        button_frame.pack(pady=20)

        self.journal_search_btn = ctk.CTkButton(button_frame, text="开始检索", command=self.start_journal_search,
                                                width=120, height=40)
        self.journal_search_btn.pack(side="left", padx=10)

        self.journal_export_btn = ctk.CTkButton(button_frame, text="导出数据", command=self.export_journal_data,
                                                width=120, height=40, state="disabled")
        self.journal_export_btn.pack(side="left", padx=10)

        # 结果框
        result_frame = ctk.CTkFrame(tab)
        result_frame.pack(pady=10, padx=20, fill="both", expand=True)

        ctk.CTkLabel(result_frame, text="检索结果:", font=("Arial", 16, "bold")).pack(anchor="w", pady=10)

        self.journal_result_text = ctk.CTkTextbox(result_frame, font=("Arial", 11))
        self.journal_result_text.pack(pady=10, padx=10, fill="both", expand=True)

        # 状态
        self.journal_status_label = ctk.CTkLabel(tab, text="就绪")
        self.journal_status_label.pack(pady=10)

        self.journal_results = []

    def setup_batch_tab(self):
        """设置批量处理选项卡"""
        tab = self.tabview.tab("批量处理")

        # 标题
        title_label = ctk.CTkLabel(tab, text="批量链接处理", font=("Arial", 20, "bold"))
        title_label.pack(pady=20)

        # 文件选择
        file_frame = ctk.CTkFrame(tab)
        file_frame.pack(pady=10, padx=20, fill="x")

        ctk.CTkLabel(file_frame, text="链接文件:", font=("Arial", 14)).grid(row=0, column=0, padx=10, pady=10,
                                                                            sticky="w")

        self.file_path_var = ctk.StringVar()
        self.file_entry = ctk.CTkEntry(file_frame, textvariable=self.file_path_var, width=400)
        self.file_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.browse_btn = ctk.CTkButton(file_frame, text="浏览", command=self.browse_file, width=80)
        self.browse_btn.grid(row=0, column=2, padx=10, pady=10)

        # 按钮
        button_frame = ctk.CTkFrame(tab)
        button_frame.pack(pady=20)

        self.batch_process_btn = ctk.CTkButton(button_frame, text="开始处理", command=self.start_batch_process,
                                               width=120, height=40)
        self.batch_process_btn.pack(side="left", padx=10)

        self.batch_export_btn = ctk.CTkButton(button_frame, text="导出数据", command=self.export_batch_data, width=120,
                                              height=40, state="disabled")
        self.batch_export_btn.pack(side="left", padx=10)

        # 进度条
        progress_frame = ctk.CTkFrame(tab)
        progress_frame.pack(pady=10, padx=20, fill="x")

        ctk.CTkLabel(progress_frame, text="处理进度:").pack(anchor="w", pady=10)

        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.pack(pady=10, padx=10, fill="x")
        self.progress_bar.set(0)

        # 结果框
        result_frame = ctk.CTkFrame(tab)
        result_frame.pack(pady=10, padx=20, fill="both", expand=True)

        ctk.CTkLabel(result_frame, text="处理结果:", font=("Arial", 16, "bold")).pack(anchor="w", pady=10)

        self.batch_result_text = ctk.CTkTextbox(result_frame, font=("Arial", 11))
        self.batch_result_text.pack(pady=10, padx=10, fill="both", expand=True)

        # 状态
        self.batch_status_label = ctk.CTkLabel(tab, text="就绪")
        self.batch_status_label.pack(pady=10)

        self.batch_results = []

    def browse_file(self):
        """浏览文件"""
        filename = filedialog.askopenfilename(filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")])
        if filename:
            self.file_path_var.set(filename)

    def start_keyword_search(self):
        """开始关键词检索"""
        keyword = self.keyword_entry.get().strip()
        if not keyword:
            messagebox.showerror("错误", "请输入关键词")
            return

        count = int(self.keyword_count_var.get())

        self.keyword_search_btn.configure(state="disabled")
        self.keyword_export_btn.configure(state="disabled")
        self.keyword_status_label.configure(text="检索中...")

        thread = threading.Thread(target=self._keyword_search_thread, args=(keyword, count))
        thread.daemon = True
        thread.start()

    def _keyword_search_thread(self, keyword, count):
        """关键词检索线程"""
        try:
            # 这里应该调用实际的爬虫代码
            # 为了演示，我们模拟一些数据
            import random
            time.sleep(2)  # 模拟网络延迟

            results = []
            for i in range(min(count, 10)):  # 最多10条演示数据
                results.append({
                    'title': f"{keyword}相关论文标题 {i + 1}",
                    'abstract': f"这是关于{keyword}的论文摘要，包含相关研究内容...",
                    'year': str(2020 + i % 5),
                    'link': f"https://example.com/paper{i + 1}"
                })

            self.keyword_results = results
            self.root.after(0, self._update_keyword_results, results)

        except Exception as e:
            self.root.after(0, self._show_keyword_error, str(e))

    def _update_keyword_results(self, results):
        """更新关键词检索结果"""
        self.keyword_result_text.delete("1.0", "end")

        if not results:
            self.keyword_result_text.insert("end", "未找到相关文献")
        else:
            for i, paper in enumerate(results, 1):
                self.keyword_result_text.insert("end", f"{i}. {paper['title']}\n")
                self.keyword_result_text.insert("end", f"   年份: {paper['year']}\n")
                self.keyword_result_text.insert("end", f"   摘要: {paper['abstract']}\n")
                self.keyword_result_text.insert("end", "-" * 60 + "\n")

        self.keyword_status_label.configure(text=f"检索完成，找到 {len(results)} 篇文献")
        self.keyword_search_btn.configure(state="normal")
        self.keyword_export_btn.configure(state="normal")

    def _show_keyword_error(self, error_msg):
        """显示关键词检索错误"""
        messagebox.showerror("错误", f"检索失败: {error_msg}")
        self.keyword_status_label.configure(text="检索失败")
        self.keyword_search_btn.configure(state="normal")

    def start_journal_search(self):
        """开始期刊检索"""
        issn = self.issn_entry.get().strip()
        if not issn:
            messagebox.showerror("错误", "请输入ISSN号")
            return

        start_year = int(self.start_year_var.get())
        end_year = int(self.end_year_var.get())
        count = int(self.journal_count_var.get())

        if start_year > end_year:
            messagebox.showerror("错误", "起始年份不能大于结束年份")
            return

        self.journal_search_btn.configure(state="disabled")
        self.journal_export_btn.configure(state="disabled")
        self.journal_status_label.configure(text="检索中...")

        thread = threading.Thread(target=self._journal_search_thread, args=(issn, [start_year, end_year], count))
        thread.daemon = True
        thread.start()

    def _journal_search_thread(self, issn, year_range, count):
        """期刊检索线程"""
        try:
            # 这里应该调用实际的爬虫代码
            import random
            time.sleep(3)  # 模拟网络延迟

            results = []
            for i in range(min(count, 15)):  # 最多15条演示数据
                results.append({
                    'title': f"期刊论文标题 {i + 1}",
                    'abstract': f"这是期刊ISSN {issn} 在 {year_range[0]}-{year_range[1]} 期间的论文摘要...",
                    'year': str(random.randint(year_range[0], year_range[1])),
                    'link': f"https://example.com/journal{i + 1}"
                })

            self.journal_results = results
            self.root.after(0, self._update_journal_results, results)

        except Exception as e:
            self.root.after(0, self._show_journal_error, str(e))

    def _update_journal_results(self, results):
        """更新期刊检索结果"""
        self.journal_result_text.delete("1.0", "end")

        if not results:
            self.journal_result_text.insert("end", "未找到相关文献")
        else:
            for i, paper in enumerate(results, 1):
                self.journal_result_text.insert("end", f"{i}. {paper['title']}\n")
                self.journal_result_text.insert("end", f"   年份: {paper['year']}\n")
                self.journal_result_text.insert("end", f"   摘要: {paper['abstract']}\n")
                self.journal_result_text.insert("end", "-" * 60 + "\n")

        self.journal_status_label.configure(text=f"检索完成，找到 {len(results)} 篇文献")
        self.journal_search_btn.configure(state="normal")
        self.journal_export_btn.configure(state="normal")

    def _show_journal_error(self, error_msg):
        """显示期刊检索错误"""
        messagebox.showerror("错误", f"检索失败: {error_msg}")
        self.journal_status_label.configure(text="检索失败")
        self.journal_search_btn.configure(state="normal")

    def start_batch_process(self):
        """开始批量处理"""
        file_path = self.file_path_var.get()
        if not file_path or not os.path.exists(file_path):
            messagebox.showerror("错误", "请选择有效的链接文件")
            return

        self.batch_process_btn.configure(state="disabled")
        self.batch_export_btn.configure(state="disabled")
        self.batch_status_label.configure(text="处理中...")
        self.progress_bar.set(0)

        thread = threading.Thread(target=self._batch_process_thread, args=(file_path,))
        thread.daemon = True
        thread.start()

    def _batch_process_thread(self, file_path):
        """批量处理线程"""
        try:
            # 读取链接文件
            with open(file_path, 'r', encoding='utf-8') as f:
                links = [line.strip() for line in f if line.strip()]

            if not links:
                self.root.after(0, lambda: messagebox.showerror("错误", "链接文件为空"))
                return

            total_links = len(links)
            results = []

            # 模拟处理过程
            for i, link in enumerate(links):
                time.sleep(0.5)  # 模拟处理延迟

                # 模拟结果
                results.append({
                    'title': f"批量处理论文 {i + 1}",
                    'abstract': f"这是从链接 {link} 获取的论文摘要...",
                    'link': link
                })

                # 更新进度
                progress = (i + 1) / total_links
                self.root.after(0, self._update_batch_progress, progress, f"已处理 {i + 1}/{total_links}")

            self.batch_results = results
            self.root.after(0, self._update_batch_results, results)

        except Exception as e:
            self.root.after(0, self._show_batch_error, str(e))

    def _update_batch_progress(self, progress, message):
        """更新批量处理进度"""
        self.progress_bar.set(progress)
        self.batch_status_label.configure(text=message)

    def _update_batch_results(self, results):
        """更新批量处理结果"""
        self.batch_result_text.delete("1.0", "end")

        if not results:
            self.batch_result_text.insert("end", "处理完成，但未获取到有效数据")
        else:
            self.batch_result_text.insert("end", f"处理完成！成功获取 {len(results)} 篇文献摘要\n\n")

            for i, paper in enumerate(results[:5], 1):  # 只显示前5条
                self.batch_result_text.insert("end", f"{i}. {paper['title']}\n")
                self.batch_result_text.insert("end", f"   摘要: {paper['abstract']}\n")
                self.batch_result_text.insert("end", "-" * 60 + "\n")

        self.batch_status_label.configure(text=f"处理完成，成功 {len(results)} 篇")
        self.batch_process_btn.configure(state="normal")
        self.batch_export_btn.configure(state="normal")

    def _show_batch_error(self, error_msg):
        """显示批量处理错误"""
        messagebox.showerror("错误", f"处理失败: {error_msg}")
        self.batch_status_label.configure(text="处理失败")
        self.batch_process_btn.configure(state="normal")

    def export_keyword_data(self):
        """导出关键词数据"""
        if not self.keyword_results:
            messagebox.showwarning("警告", "没有数据可导出")
            return

        keyword = self.keyword_entry.get().strip()
        filename = f"data/keyword/{keyword}_results.csv"

        # 确保目录存在
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        # 导出CSV
        df = pd.DataFrame(self.keyword_results)
        df.to_csv(filename, index=False, encoding='utf-8-sig')

        messagebox.showinfo("成功", f"数据已导出到: {filename}")

    def export_journal_data(self):
        """导出期刊数据"""
        if not self.journal_results:
            messagebox.showwarning("警告", "没有数据可导出")
            return

        issn = self.issn_entry.get().strip()
        filename = f"data/journal/{issn}_results.csv"

        # 确保目录存在
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        # 导出CSV
        df = pd.DataFrame(self.journal_results)
        df.to_csv(filename, index=False, encoding='utf-8-sig')

        messagebox.showinfo("成功", f"数据已导出到: {filename}")

    def export_batch_data(self):
        """导出批量处理数据"""
        if not self.batch_results:
            messagebox.showwarning("警告", "没有数据可导出")
            return

        # 使用文件名作为基础名称
        base_name = os.path.splitext(os.path.basename(self.file_path_var.get()))[0]
        filename = f"data/processed/{base_name}_results.csv"

        # 确保目录存在
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        # 导出CSV
        df = pd.DataFrame(self.batch_results)
        df.to_csv(filename, index=False, encoding='utf-8-sig')

        messagebox.showinfo("成功", f"数据已导出到: {filename}")

    def run(self):
        """运行应用程序"""
        self.root.mainloop()


if __name__ == "__main__":
    app = CNKISpiderGUI()
    app.run()