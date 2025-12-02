# CNKI 学术文献数据采集系统

## 📖 项目简介

本项目是一个面向大语言模型领域微调的学术文献数据采集系统，专门针对中国知网（CNKI）设计开发。系统通过自动化爬虫技术，高效采集学术文献的标题-摘要对，并将其转换为标准的大模型微调数据格式（JSONL），为领域专用大模型的训练提供高质量数据支持。

## ✨ 核心功能

### 🔍 关键词主题检索

- 支持任意领域关键词检索
    
- 可设置爬取数量限制（1-500篇）
    
- 自动翻页获取多页结果
    
- 实时结果显示与预览
    

### 📚 期刊定向采集

- 通过ISSN号精准锁定特定期刊
    
- 支持年份范围设置（如2020-2024）
    
- 自动遍历期刊各年期数
    
- 多重选择器策略确保链接提取稳定性
    

### 📄 文献详情解析

- 批量处理文献URL列表
    
- 智能识别多种页面模板
    
- 精准提取标题和摘要内容
    
- 支持断点续传和进度显示
    

### 🎨 图形用户界面

- 选项卡式布局，功能分区明确
    
- 实时日志输出，操作状态可视化
    
- 数据统计与词云分析
    
- 一键转换为JSONL微调格式
    

## 🛠️ 技术架构

### 技术栈

- **动态网页抓取**: Selenium 4.27.1
    
- **图形用户界面**: PyQt5 5.15.11
    
- **数据处理**: Pandas 2.0.3
    
- **数据可视化**: Matplotlib 3.7.5
    
- **数据清洗**: BeautifulSoup4 4.14.2
    

### 系统架构

text

表现层 (UI Layer)
├── 关键词检索标签页
├── 期刊采集标签页
└── 数据分析标签页

业务逻辑层 (Business Layer)
├── 关键词爬虫线程 (KeywordWorker)
├── 期刊链接采集线程 (IssnLinkWorker)
└── 详情解析线程 (DetailWorker)

数据访问层 (Data Layer)
├── 链接存储 (links/)
├── 原始结果 (raw_results/)
└── 微调数据 (fine_tune_data/)

## 🚀 快速开始

### 环境要求

- Python 3.8+
    
- Chrome浏览器 120.0+
    
- 对应的ChromeDriver
    

### 安装步骤

1. **克隆项目**
    

bash

git clone https://github.com/yourusername/cnki-crawler.git
cd cnki-crawler

2. **安装依赖**
    

bash

pip install -r requirements.txt

3. **配置ChromeDriver**
    
    - 下载与Chrome版本匹配的ChromeDriver
        
    - 修改 `src/config.py` 中的路径配置
        
4. **运行程序**
    

bash

python src/main.py

### 详细配置

**requirements.txt 内容：**

text

beautifulsoup4>=4.14.2
selenium>=4.38.0
pandas>=2.3.2
matplotlib>=3.10.6
pyqt5>=5.15.11
wordcloud>=1.9.4

**config.py 关键配置：**

python

CHROME_DRIVER_PATH = r'C:\Program Files\Google\Chrome\Application\chromedriver.exe'

## 📖 使用指南

### 1. 关键词检索

1. 在"关键词检索"标签页输入目标关键词
    
2. 设置需要爬取的数量
    
3. 点击"开始检索"按钮
    
4. 查看实时日志和结果表格
    

### 2. 期刊采集

1. 在"期刊/详情采集"标签页选择期刊（支持手动输入ISSN）
    
2. 设置年份范围
    
3. 点击"获取期刊链接"按钮
    
4. 选择生成的链接文件，点击"批量爬取详情"
    

### 3. 数据分析与转换

1. 在"数据分析与转换"标签页加载CSV文件
    
2. 查看词云分析和数据统计
    
3. 点击"转换为大模型微调数据"生成JSONL文件
    

## 📂 项目结构

text

CNKI_Crawler_Project/
├── src/                    # 源代码目录
│   ├── config.py          # 配置文件
│   ├── workers.py         # 爬虫工作线程
│   ├── utils.py           # 工具函数
│   ├── main_window.py     # 主窗口界面
│   └── main.py            # 程序入口
├── data/                  # 数据存储目录
│   ├── links/            # 文献链接文件
│   ├── raw_results/      # 原始采集数据
│   └── fine_tune_data/   # 微调格式数据
├── requirements.txt       # 依赖包列表
└── README.md             # 项目说明文档

## 🔧 反爬虫策略应对

系统采用多层次反检测策略：

- **浏览器指纹伪装**：移除webdriver特征，禁用自动化控制
    
- **智能等待机制**：检测验证码并预留人工处理时间
    
- **随机延时**：模拟人类操作间隔，避免访问过快
    
- **多重选择器**：应对页面结构变化，提高提取稳定性
    

## 📊 数据格式说明

### 原始数据格式（CSV）

csv

title,abstract,link,year
"文献标题","文献摘要","https://example.com/article",2024

### 微调数据格式（JSONL）

json

{
  "messages": [
    {"role": "system", "content": "你是一个专业的学术科研助手。"},
    {"role": "user", "content": "请介绍一下关于《文献标题》的研究内容。"},
    {"role": "assistant", "content": "文献摘要内容..."}
  ]
}

## 🧪 测试结果

### 功能测试

- 关键词检索：成功采集100篇文献，准确率100%
    
- 期刊采集：成功遍历《水利学报》2023年12期，获取200+条链接
    
- 详情解析：批量处理100+文献，标题-摘要匹配准确率100%
    

### 数据质量

- 有效数据率：98%（剔除无摘要文献）
    
- 格式正确率：100%
    
- 编码兼容性：支持UTF-8，Excel无乱码
    

## 🤝 贡献指南

欢迎贡献代码！请按以下步骤操作：

1. Fork 本仓库
    
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
    
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
    
4. 推送到分支 (`git push origin feature/AmazingFeature`)
    
5. 开启 Pull Request
    

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](https://license/) 文件了解详情

## 📞 联系我们

如有问题或建议，请通过以下方式联系我们：

- 提交 [Issues](https://github.com/yourusername/cnki-crawler/issues)
    
- 发送邮件至：19270859916@163.com
    

## 🙏 致谢

感谢以下开源项目的支持：

- [Selenium](https://www.selenium.dev/) - 浏览器自动化框架
    
- [PyQt5](https://www.riverbankcomputing.com/software/pyqt/) - Python GUI框架
    
- [Pandas](https://pandas.pydata.org/) - 数据处理库
    

---

<div align="center">

**⭐ 如果这个项目对您有帮助，请给我们一个 Star！⭐**

</div>