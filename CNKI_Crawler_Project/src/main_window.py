import os
import sys
import pandas as pd
import jieba
from wordcloud import WordCloud

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QTextEdit,
                             QTabWidget, QSpinBox, QComboBox, QFileDialog,
                             QProgressBar, QTableWidget, QTableWidgetItem,
                             QHeaderView, QMessageBox, QGroupBox, QGridLayout)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

# Matplotlib 集成
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
from matplotlib import rcParams

# 设置 Matplotlib 中文字体 (防止乱码)
rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
rcParams['axes.unicode_minus'] = False

from .workers import KeywordWorker, IssnLinkWorker, DetailWorker
from .config import PRESET_ISSNS, LINK_DIR, RESULT_DIR
from .utils import convert_csv_to_jsonl


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CNKI 文献采集与大模型数据处理系统")
        self.resize(1100, 800)

        # === 优化 1: 全局调大字体 ===
        # 使用样式表设置全局字体大小和类型
        self.setStyleSheet("""
            QWidget {
                font-size: 14px;
                font-family: "Microsoft YaHei", "SimHei";
            }
            QGroupBox {
                font-weight: bold;
                font-size: 15px;
                margin-top: 10px;
            }
            QPushButton {
                padding: 6px 12px;
                font-weight: bold;
            }
            QHeaderView::section {
                font-size: 14px;
            }
        """)

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
        self.log_area.setMaximumHeight(180)
        self.log_area.setStyleSheet("font-family: Consolas; font-size: 13px;")  # 日志保留等宽字体

        log_label = QLabel("系统运行日志:")
        log_label.setStyleSheet("font-weight: bold; color: #555;")
        self.layout.addWidget(log_label)
        self.layout.addWidget(self.log_area)

    def log(self, msg):
        self.log_area.append(f" >> {msg}")
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())

    # --- Tab 1: 关键词检索 ---
    def init_keyword_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 输入区容器
        group = QGroupBox("检索设置")
        group_layout = QHBoxLayout(group)
        group_layout.setAlignment(Qt.AlignVCenter)  # 垂直居中

        self.kw_input = QLineEdit()
        self.kw_input.setPlaceholderText("请输入关键词 (例如: 城市洪涝)")
        self.kw_input.setMinimumHeight(35)

        self.kw_count = QSpinBox()
        self.kw_count.setRange(1, 1000)
        self.kw_count.setValue(20)
        self.kw_count.setPrefix("爬取数量: ")
        self.kw_count.setMinimumHeight(35)
        self.kw_count.setMinimumWidth(120)

        btn_start = QPushButton("开始检索")
        btn_start.setMinimumHeight(35)
        btn_start.clicked.connect(self.start_keyword_task)

        group_layout.addWidget(QLabel("关键词:"))
        group_layout.addWidget(self.kw_input)
        group_layout.addSpacing(15)
        group_layout.addWidget(self.kw_count)
        group_layout.addSpacing(15)
        group_layout.addWidget(btn_start)

        layout.addWidget(group)

        # 结果预览表
        self.kw_table = QTableWidget()
        self.kw_table.setColumnCount(3)
        self.kw_table.setHorizontalHeaderLabels(["标题", "年份", "链接"])
        self.kw_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.kw_table)

        self.tabs.addTab(tab, "关键词检索")

    def start_keyword_task(self):
        kw = self.kw_input.text()
        if not kw:
            QMessageBox.warning(self, "提示", "请输入关键词")
            return
        self.worker = KeywordWorker(kw, self.kw_count.value())
        self.worker.log_signal.connect(self.log)
        self.worker.finish_signal.connect(self.on_keyword_finished)
        self.worker.start()
        self.log(f"启动关键词任务: {kw}")

    def on_keyword_finished(self, path):
        self.log(f"任务完成，文件已保存: {path}")
        QMessageBox.information(self, "完成", f"数据已保存至:\n{path}")
        try:
            df = pd.read_csv(path)
            self.kw_table.setRowCount(len(df))
            for i, row in df.iterrows():
                self.kw_table.setItem(i, 0, QTableWidgetItem(str(row.get('title', ''))))
                self.kw_table.setItem(i, 1, QTableWidgetItem(str(row.get('year', ''))))
                self.kw_table.setItem(i, 2, QTableWidgetItem(str(row.get('link', ''))))
        except Exception as e:
            self.log(f"读取结果文件失败: {e}")

    # --- Tab 2: 期刊ISSN采集 (重点优化布局) ---
    def init_issn_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # === 步骤1: 获取链接 (优化布局) ===
        group1 = QGroupBox("第一步：获取期刊文献链接")
        # 使用 Grid 布局解决对齐问题
        grid_layout = QGridLayout(group1)
        grid_layout.setVerticalSpacing(15)  # 行间距
        grid_layout.setHorizontalSpacing(10)

        # 1. 期刊选择行
        lbl_issn = QLabel("选择/输入期刊:")
        self.issn_combo = QComboBox()
        self.issn_combo.setEditable(True)
        self.issn_combo.setMinimumHeight(35)
        self.issn_combo.setMinimumWidth(300)  # 优化3: 增加宽度防止按钮消失
        self.issn_combo.addItems([f"{k} ({v})" for k, v in PRESET_ISSNS.items()])
        # 强制显示下拉箭头样式
        self.issn_combo.setStyleSheet("QComboBox { combobox-popup: 0; }")

        grid_layout.addWidget(lbl_issn, 0, 0)
        grid_layout.addWidget(self.issn_combo, 0, 1, 1, 4)  # 跨4列

        # 2. 年份选择行 (优化4: 对齐问题)
        lbl_year = QLabel("年份范围:")

        self.year_start = QSpinBox()
        self.year_start.setRange(2000, 2025)
        self.year_start.setValue(2024)
        self.year_start.setMinimumHeight(35)
        self.year_start.setSuffix(" 年")

        lbl_to = QLabel(" 至 ")
        lbl_to.setAlignment(Qt.AlignCenter)

        self.year_end = QSpinBox()
        self.year_end.setRange(2000, 2025)
        self.year_end.setValue(2024)
        self.year_end.setMinimumHeight(35)
        self.year_end.setSuffix(" 年")

        btn_get_links = QPushButton("开始抓取链接")
        btn_get_links.setMinimumHeight(35)
        btn_get_links.clicked.connect(self.start_issn_task)

        # 布局放入 Grid
        grid_layout.addWidget(lbl_year, 1, 0)
        grid_layout.addWidget(self.year_start, 1, 1)
        grid_layout.addWidget(lbl_to, 1, 2)
        grid_layout.addWidget(self.year_end, 1, 3)
        grid_layout.addWidget(btn_get_links, 1, 4)

        # 设置列比例，让控件紧凑
        grid_layout.setColumnStretch(1, 1)
        grid_layout.setColumnStretch(3, 1)
        grid_layout.setColumnStretch(4, 0)

        layout.addWidget(group1)

        # === 步骤2: 详情爬取 ===
        group2 = QGroupBox("第二步：批量爬取摘要")
        l2 = QHBoxLayout(group2)
        l2.setAlignment(Qt.AlignVCenter)

        self.link_file_label = QLabel("未选择文件")
        self.link_file_label.setStyleSheet("color: #888; border: 1px dashed #aaa; padding: 5px;")

        btn_select_file = QPushButton("选择链接文件(.txt)")
        btn_select_file.setMinimumHeight(35)
        btn_select_file.clicked.connect(self.select_link_file)

        btn_run_detail = QPushButton("开始爬取详情")
        btn_run_detail.setMinimumHeight(35)
        btn_run_detail.clicked.connect(self.start_detail_task)

        l2.addWidget(btn_select_file)
        l2.addWidget(self.link_file_label, 1)  # 伸缩因子1，占据剩余空间
        l2.addWidget(btn_run_detail)

        layout.addWidget(group2)

        # 进度条 (修复点: 使用 setFixedHeight)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(15)
        layout.addWidget(self.progress_bar)

        layout.addStretch()
        self.tabs.addTab(tab, "期刊/详情采集")

    def start_issn_task(self):
        text = self.issn_combo.currentText()
        import re
        match = re.search(r'\d{4}-[\dxX]{4}', text)  # 支持ISSN含X的情况
        if match:
            issn = match.group()
        else:
            issn = text

        if not issn:
            QMessageBox.warning(self, "错误", "请输入有效的ISSN")
            return

        self.issn_worker = IssnLinkWorker(issn, self.year_start.value(), self.year_end.value())
        self.issn_worker.log_signal.connect(self.log)
        self.issn_worker.finish_signal.connect(lambda p: QMessageBox.information(self, "完成", f"链接已保存: {p}"))
        self.issn_worker.start()

    def select_link_file(self):
        fname, _ = QFileDialog.getOpenFileName(self, '选择链接文件', LINK_DIR, "Text Files (*.txt)")
        if fname:
            self.link_file_label.setText(fname)
            self.link_file_label.setStyleSheet("color: black; border: 1px solid green; padding: 5px;")

    def start_detail_task(self):
        path = self.link_file_label.text()
        if not os.path.exists(path):
            QMessageBox.warning(self, "提示", "请先选择有效的链接文件")
            return

        self.detail_worker = DetailWorker(path)
        self.detail_worker.log_signal.connect(self.log)
        self.detail_worker.progress_signal.connect(self.progress_bar.setValue)
        self.detail_worker.finish_signal.connect(lambda p: QMessageBox.information(self, "完成", f"详情已保存: {p}"))
        self.detail_worker.start()

    # --- Tab 3: 数据分析与转换 (优化 2: 词云图) ---
    def init_analysis_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 工具栏
        tool_layout = QHBoxLayout()
        btn_load = QPushButton("加载 CSV 结果文件")
        btn_load.setMinimumHeight(40)
        btn_load.clicked.connect(self.load_csv_for_viz)

        btn_convert = QPushButton("转换为大模型微调数据(JSONL)")
        btn_convert.setMinimumHeight(40)
        btn_convert.clicked.connect(self.convert_data)

        tool_layout.addWidget(btn_load)
        tool_layout.addWidget(btn_convert)
        layout.addLayout(tool_layout)

        # 图表区域
        self.figure = plt.figure(figsize=(6, 5))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        self.current_csv = None
        self.tabs.addTab(tab, "数据分析与转换")

    def load_csv_for_viz(self):
        fname, _ = QFileDialog.getOpenFileName(self, '选择结果文件', RESULT_DIR, "CSV Files (*.csv)")
        if fname:
            self.current_csv = fname
            try:
                df = pd.read_csv(fname)
                self.log(f"加载数据成功，共 {len(df)} 条")

                if 'title' not in df.columns:
                    QMessageBox.warning(self, "错误", "CSV文件中未找到 'title' 列，无法生成词云。")
                    return

                # === 生成词云图逻辑 ===
                self.log("正在生成词云图...")

                # 1. 结巴分词
                text_list = []
                for title in df['title'].dropna().astype(str):
                    # 过滤掉无意义的短词
                    seg_list = [x for x in jieba.cut(title) if len(x) > 1]
                    text_list.extend(seg_list)

                text_content = " ".join(text_list)

                if not text_content.strip():
                    self.log("数据为空或分词结果为空")
                    return

                # 2. 设置字体路径 (Windows默认路径)
                font_path = "C:/Windows/Fonts/simhei.ttf"
                if not os.path.exists(font_path):
                    # 尝试其他备用字体
                    font_path = "C:/Windows/Fonts/msyh.ttf"

                # 3. 生成词云
                wc = WordCloud(
                    font_path=font_path,
                    background_color='white',
                    width=800,
                    height=600,
                    max_words=100,
                    collocations=False  # 避免重复词
                ).generate(text_content)

                # 4. 绘图
                self.figure.clear()
                ax = self.figure.add_subplot(111)
                ax.imshow(wc, interpolation='bilinear')
                ax.axis('off')  # 不显示坐标轴
                ax.set_title(f"文献标题词云分析 (N={len(df)})", fontsize=14)

                self.canvas.draw()
                self.log("词云图生成完毕")

            except Exception as e:
                self.log(f"可视化失败: {e}")
                QMessageBox.critical(self, "错误", f"分析失败: {str(e)}")

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