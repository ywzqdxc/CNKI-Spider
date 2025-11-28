import os

# 基础路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
LINK_DIR = os.path.join(DATA_DIR, 'links')
RESULT_DIR = os.path.join(DATA_DIR, 'raw_results')
FINETUNE_DIR = os.path.join(DATA_DIR, 'fine_tune_data')

# 确保目录存在
for d in [LINK_DIR, RESULT_DIR, FINETUNE_DIR]:
    if not os.path.exists(d):
        os.makedirs(d)

# ChromeDriver 路径 (请根据实际情况修改)
CHROME_DRIVER_PATH = r'C:\Program Files\Google\Chrome\Application\chromedriver.exe'

# 常用期刊 ISSN 预设
PRESET_ISSNS = {
    "水利学报": "0577-9154",
    "软件学报": "1000-9825",
    "计算机学报": "0254-4164",
    "土木工程学报": "1000-131X",
    "自动化学报": "0254-4156",
    "中国科学:技术科学": "1674-7259"
}