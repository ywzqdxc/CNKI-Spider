import os
import random
import time
import sys
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ================= 配置区域 =================
DEBUG = True
HEADLESS = False  # 调试期间建议设为 False，稳定后可改为 True
CHROME_DRIVER_PATH = r'C:\Program Files\Google\Chrome\Application\chromedriver.exe'  # 请务必修改为你的路径
DATA_DIR = 'data_results'  # 结果保存目录
LINK_DIR = 'links'  # 链接文件目录
MAX_WORKERS = 2  # 并发线程数
BATCH_SIZE = 30  # 每处理多少个链接重启一次浏览器
MAX_RETRIES = 3  # 单个链接最大重试次数

# ================= 日志配置 =================
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)


def ensure_directory(directory: str) -> None:
    """确保目录存在"""
    if not os.path.exists(directory):
        os.makedirs(directory)


def load_chrome_driver() -> webdriver.Chrome:
    """加载防检测的 Chrome 驱动"""
    options = webdriver.ChromeOptions()
    service = Service(CHROME_DRIVER_PATH)

    if HEADLESS:
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-images')

    # 反爬虫检测配置
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(service=service, options=options)

    # 移除 webdriver 标识
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    return driver


def simulate_human_behavior(driver: webdriver.Chrome) -> None:
    """
    模拟人类行为（闲逛），降低触发验证码的概率
    """
    logging.info("正在进行人类行为模拟(闲逛)...")
    try:
        # 1. 访问首页
        driver.get('https://kns.cnki.net/kns8s/defaultresult/index')
        time.sleep(random.uniform(1, 2))

        # 2. 模拟一次搜索
        driver.get('https://kns.cnki.net/kns8s/defaultresult/index?kw=经济')
        time.sleep(random.uniform(1.5, 3))

        # 3. 模拟进入一个页面并刷新
        # 使用一个较新的固定链接或者随机链接
        test_url = 'https://kns.cnki.net/kcms2/article/abstract?v=random_check'
        driver.get(test_url)
        for _ in range(2):
            driver.refresh()
            time.sleep(random.uniform(0.5, 1.0))

    except Exception as e:
        logging.warning(f"闲逛模拟中出现非致命错误: {e}")


def clean_title_text(raw_text: str) -> str:
    """
    清洗标题文本：
    输入: "信心加速器...有效性\n郭豫媚 郭俊杰\n中央财经大学金融学院"
    输出: "信心加速器...有效性"
    """
    if not raw_text:
        return ""
    # 按换行符分割，取第一部分，并去除首尾空格
    return raw_text.split('\n')[0].strip()


def attempt_scrape(driver: webdriver.Chrome, link: str, index: int) -> dict:
    """
    尝试爬取单篇文章的标题和摘要
    :return: 成功返回 {'title': '...', 'abstract': '...'}，失败返回 None
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            driver.get(link)

            # === 跳过验证码/加载脚本 ===
            try:
                driver.execute_script("redirectNewLink()")
            except Exception:
                pass  # 页面没有该函数则忽略

            # 等待标题出现
            try:
                WebDriverWait(driver, 6).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".wx-tit, h1"))
                )
            except Exception:
                # 超时则刷新重试
                driver.refresh()
                time.sleep(1.5)
                try:
                    driver.execute_script("redirectNewLink()")
                except:
                    pass

            # === 检查是否触发滑块或验证码 ===
            if "拼图校验" in driver.page_source or "waf_verify" in driver.current_url:
                logging.warning(f"Article {index}: 触发验证码 (Attempt {attempt})")
                time.sleep(random.uniform(3, 5))
                if attempt == MAX_RETRIES:
                    return None
                continue

            # === 1. 提取并清洗标题 ===
            # 知网详情页标题通常在 .wx-tit 中
            title_ele = driver.find_element(By.CSS_SELECTOR, ".wx-tit")
            raw_title = title_ele.text
            clean_title = clean_title_text(raw_title)

            # === 2. 提取摘要 ===
            abstract = ""
            try:
                # 新版摘要通常在 .abstract-text
                abs_ele = driver.find_element(By.CSS_SELECTOR, ".abstract-text")
                abstract = abs_ele.text.strip()
            except Exception:
                try:
                    # 旧版兼容 #ChDivSummary
                    abs_ele = driver.find_element(By.CSS_SELECTOR, "#ChDivSummary")
                    abstract = abs_ele.text.strip()
                except Exception:
                    abstract = "无摘要"

            logging.info(f"Article {index} Success: {clean_title[:15]}...")

            # === 返回结果（不包含 url） ===
            return {
                "title": clean_title,
                "abstract": abstract
            }

        except Exception as e:
            logging.error(f"Article {index} error on attempt {attempt}: {e}")
            time.sleep(random.uniform(1, 2))

    return None


def process_journal_year(name: str, year: str, links: list) -> None:
    """
    处理任务并保存 CSV/JSON
    """
    save_base_name = os.path.join(DATA_DIR, f"{name}_{year}")
    ensure_directory(DATA_DIR)

    results = []
    skipped_links = []

    driver = None

    try:
        driver = load_chrome_driver()
        simulate_human_behavior(driver)

        logging.info(f"开始处理 {name} {year}, 共 {len(links)} 篇文章")

        for idx, link in enumerate(links):
            # 批次重启逻辑
            if idx > 0 and idx % BATCH_SIZE == 0:
                logging.info(f"已处理 {idx} 篇，重启浏览器以刷新环境...")
                if driver:
                    driver.quit()
                time.sleep(5)
                driver = load_chrome_driver()
                simulate_human_behavior(driver)

            # 执行爬取
            data = attempt_scrape(driver, link, idx + 1)

            if data:
                results.append(data)
            else:
                skipped_links.append(link)

            time.sleep(random.uniform(0.8, 1.5))

        # === 保存数据 ===
        if results:
            df = pd.DataFrame(results)

            # 保存 CSV
            csv_path = f"{save_base_name}.csv"
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')

            # 保存 JSON
            json_path = f"{save_base_name}.json"
            df.to_json(json_path, orient='records', force_ascii=False, indent=4)

            logging.info(f"结果已保存: {csv_path}")

        # 记录失败链接
        if skipped_links:
            logging.warning(f"{name} {year} 有 {len(skipped_links)} 篇失败，保存到 failed.txt")
            with open(f"{save_base_name}_failed.txt", "w", encoding="utf-8") as f:
                for sl in skipped_links:
                    f.write(sl + "\n")

    except Exception as e:
        logging.error(f"处理 {name} {year} 时发生错误: {e}")
    finally:
        if driver:
            driver.quit()


def process_txt_file(file_path: str) -> None:
    """读取 txt 文件并分发任务"""
    base_name = os.path.basename(file_path)
    try:
        # 文件名格式要求: 期刊名_年份.txt
        name_part, year_part = base_name.rsplit('_', 1)
        year = year_part.split('.')[0]
    except Exception as e:
        logging.error(f"文件名格式解析错误 {base_name}: {e}")
        return

    # 简单断点续传：如果CSV已存在则跳过
    if os.path.exists(os.path.join(DATA_DIR, f"{name_part}_{year}.csv")):
        logging.info(f"文件 {base_name} 对应的结果已存在，跳过。")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        links = [line.strip() for line in f if line.strip()]

    if links:
        process_journal_year(name_part, year, links)
    else:
        logging.warning(f"文件 {file_path} 为空")


def main() -> None:
    """主程序入口"""
    if not os.path.exists(LINK_DIR):
        logging.error(f"链接目录 {LINK_DIR} 不存在，请先创建并放入txt文件")
        return

    txt_files = [os.path.join(LINK_DIR, f) for f in os.listdir(LINK_DIR) if f.endswith('.txt')]

    if not txt_files:
        logging.warning(f"{LINK_DIR} 目录下没有找到 txt 文件")
        return

    logging.info(f"开始处理 {len(txt_files)} 个任务文件...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_txt_file, file): file for file in txt_files}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                logging.error(f"任务执行异常: {e}")


if __name__ == '__main__':
    main()