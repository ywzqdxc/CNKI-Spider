import os
import pandas as pd
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QTextEdit,
                             QTabWidget, QSpinBox, QComboBox, QFileDialog,
                             QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
from matplotlib import rcParams

# 设置中文字体
rcParams['font.sans-serif'] = ['SimHei']
rcParams['axes.unicode_minus'] = False

from .workers import KeywordWorker, IssnLinkWorker, DetailWorker
from .config import PRESET_ISSNS, LINK_DIR, RESULT_DIR
from .utils import convert_csv_to_jsonl


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CNKI 文献采集与大模型数据处理系统")
        self.resize(1000, 700)

        # 主容器
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.layout = QVBoxLayout(main_widget)

        # 选项卡
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)

        # 初始化各个页面
        self.init_keyword_tab()
        self.init_issn_tab()
        self.init_analysis_tab()

        # 全局日志
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(150)
        self.layout.addWidget(QLabel("系统运行日志:"))
        self.layout.addWidget(self.log_area)

    def log(self, msg):
        self.log_area.append(f" >> {msg}")
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())

    # --- Tab 1: 关键词检索 ---
    def init_keyword_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 输入区
        input_layout = QHBoxLayout()
        self.kw_input = QLineEdit()
        self.kw_input.setPlaceholderText("请输入关键词 (例如: 城市洪涝)")
        self.kw_count = QSpinBox()
        self.kw_count.setRange(1, 500)
        self.kw_count.setValue(20)
        self.kw_count.setPrefix("爬取数量: ")

        btn_start = QPushButton("开始检索")
        btn_start.clicked.connect(self.start_keyword_task)

        input_layout.addWidget(QLabel("关键词:"))
        input_layout.addWidget(self.kw_input)
        input_layout.addWidget(self.kw_count)
        input_layout.addWidget(btn_start)
        layout.addLayout(input_layout)

        # 结果预览表
        self.kw_table = QTableWidget()
        self.kw_table.setColumnCount(3)
        self.kw_table.setHorizontalHeaderLabels(["标题", "年份", "链接"])
        self.kw_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.kw_table)

        self.tabs.addTab(tab, "关键词检索")

    def start_keyword_task(self):
        kw = self.kw_input.text()
        if not kw: return
        self.worker = KeywordWorker(kw, self.kw_count.value())
        self.worker.log_signal.connect(self.log)
        self.worker.finish_signal.connect(self.on_keyword_finished)
        self.worker.start()
        self.log(f"启动关键词任务: {kw}")

    def on_keyword_finished(self, path):
        self.log(f"任务完成，文件已保存: {path}")
        QMessageBox.information(self, "完成", f"数据已保存至:\n{path}")
        # 加载数据到表格
        df = pd.read_csv(path)
        self.kw_table.setRowCount(len(df))
        for i, row in df.iterrows():
            self.kw_table.setItem(i, 0, QTableWidgetItem(str(row.get('title', ''))))
            self.kw_table.setItem(i, 1, QTableWidgetItem(str(row.get('year', ''))))
            self.kw_table.setItem(i, 2, QTableWidgetItem(str(row.get('link', ''))))

    # --- Tab 2: 期刊ISSN采集 ---
    def init_issn_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 步骤1: 获取链接
        group1 = QWidget()
        l1 = QHBoxLayout(group1)

        self.issn_combo = QComboBox()
        self.issn_combo.setEditable(True)
        self.issn_combo.addItems([f"{k} ({v})" for k, v in PRESET_ISSNS.items()])

        self.year_start = QSpinBox()
        self.year_start.setRange(2000, 2025)
        self.year_start.setValue(2024)
        self.year_end = QSpinBox()
        self.year_end.setRange(2000, 2025)
        self.year_end.setValue(2024)

        btn_get_links = QPushButton("1. 获取期刊链接")
        btn_get_links.clicked.connect(self.start_issn_task)

        l1.addWidget(QLabel("选择/输入期刊:"))
        l1.addWidget(self.issn_combo)
        l1.addWidget(QLabel("年份范围:"))
        l1.addWidget(self.year_start)
        l1.addWidget(QLabel("至"))
        l1.addWidget(self.year_end)
        l1.addWidget(btn_get_links)
        layout.addWidget(group1)

        # 步骤2: 详情爬取
        group2 = QWidget()
        l2 = QHBoxLayout(group2)

        self.link_file_label = QLabel("未选择文件")
        btn_select_file = QPushButton("选择链接文件(.txt)")
        btn_select_file.clicked.connect(self.select_link_file)

        btn_run_detail = QPushButton("2. 批量爬取详情")
        btn_run_detail.clicked.connect(self.start_detail_task)

        l2.addWidget(btn_select_file)
        l2.addWidget(self.link_file_label)
        l2.addWidget(btn_run_detail)
        layout.addWidget(group2)

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        layout.addStretch()
        self.tabs.addTab(tab, "期刊/详情采集")

    def start_issn_task(self):
        text = self.issn_combo.currentText()
        # 提取ISSN
        import re
        match = re.search(r'\d{4}-\w{4}', text)
        if match:
            issn = match.group()
        else:
            issn = text  # 假设用户直接输入了ISSN

        self.issn_worker = IssnLinkWorker(issn, self.year_start.value(), self.year_end.value())
        self.issn_worker.log_signal.connect(self.log)
        self.issn_worker.finish_signal.connect(lambda p: QMessageBox.information(self, "完成", f"链接已保存: {p}"))
        self.issn_worker.start()

    def select_link_file(self):
        fname, _ = QFileDialog.getOpenFileName(self, '选择链接文件', LINK_DIR, "Text Files (*.txt)")
        if fname:
            self.link_file_label.setText(fname)

    def start_detail_task(self):
        path = self.link_file_label.text()
        if not os.path.exists(path): return

        self.detail_worker = DetailWorker(path)
        self.detail_worker.log_signal.connect(self.log)
        self.detail_worker.progress_signal.connect(self.progress_bar.setValue)
        self.detail_worker.finish_signal.connect(lambda p: QMessageBox.information(self, "完成", f"详情已保存: {p}"))
        self.detail_worker.start()

    # --- Tab 3: 数据分析与转换 ---
    def init_analysis_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        tool_layout = QHBoxLayout()
        btn_load = QPushButton("加载 CSV 结果文件")
        btn_load.clicked.connect(self.load_csv_for_viz)

        btn_convert = QPushButton("转换为大模型微调数据(JSONL)")
        btn_convert.clicked.connect(self.convert_data)

        tool_layout.addWidget(btn_load)
        tool_layout.addWidget(btn_convert)
        layout.addLayout(tool_layout)

        # 图表区域
        self.figure = plt.figure(figsize=(5, 4))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        self.current_csv = None

        self.tabs.addTab(tab, "数据分析与转换")

    def load_csv_for_viz(self):
        fname, _ = QFileDialog.getOpenFileName(self, '选择结果文件', RESULT_DIR, "CSV Files (*.csv)")
        if fname:
            self.current_csv = fname
            df = pd.read_csv(fname)
            self.log(f"加载数据成功，共 {len(df)} 条")

            # 简单的词云或统计
            self.figure.clear()
            ax = self.figure.add_subplot(111)

            # 统计标题长度分布作为示例
            if 'title' in df.columns:
                lengths = df['title'].astype(str).apply(len)
                ax.hist(lengths, bins=20, color='skyblue', edgecolor='black')
                ax.set_title("论文标题长度分布")
                ax.set_xlabel("字数")
                ax.set_ylabel("频次")

            self.canvas.draw()

    def convert_data(self):
        if not self.current_csv:
            QMessageBox.warning(self, "警告", "请先加载CSV文件")
            return

        success, msg = convert_csv_to_jsonl(self.current_csv)
        if success:
            QMessageBox.information(self, "成功", f"JSONL文件已生成:\n{msg}")
            self.log(f"转换成功: {msg}")
        else:
            QMessageBox.warning(self, "失败", f"转换失败: {msg}")