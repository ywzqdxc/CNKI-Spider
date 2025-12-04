import os
import random
import time
import sys
import logging
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ================= 配置区域 =================
DEBUG = True
HEADLESS = False  # 调试时建议设为 False，稳定后可设为 True
CHROME_DRIVER_PATH = r'C:\Program Files\Google\Chrome\Application\chromedriver.exe'  # 请修改为你的路径
DATA_DIR = '../data_results'  # 结果保存目录
LINK_DIR = '../links'  # 链接文件目录
MAX_WORKERS = 2  # 线程数
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
    """加载 Chrome 驱动"""
    options = webdriver.ChromeOptions()
    service = Service(CHROME_DRIVER_PATH)

    if HEADLESS:
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-images')  # 不加载图片加快速度

    # 常规反检测配置
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(service=service, options=options)

    # 移除 webdriver 痕迹
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    return driver


def simulate_human_behavior(driver: webdriver.Chrome) -> None:
    """
    模拟人类闲逛行为，用于建立初始信任，减少后续验证码概率
    """
    logging.info("正在进行人类行为模拟(闲逛)...")
    try:
        # 访问首页
        driver.get('https://kns.cnki.net/kns8s/defaultresult/index')
        time.sleep(random.uniform(1, 2))

        # 模拟一次无意义搜索
        driver.get('https://kns.cnki.net/kns8s/defaultresult/index?kw=人工智能')
        time.sleep(random.uniform(1.5, 3))

        # 尝试访问一个详情页并刷新几次
        el = 'https://kns.cnki.net/kcms2/article/abstract?v=random_test'
        driver.get(el)
        for _ in range(2):
            driver.refresh()
            time.sleep(random.uniform(0.5, 1.0))

    except Exception as e:
        logging.warning(f"闲逛模拟中出现小错误 (可忽略): {e}")


def attempt_scrape(driver: webdriver.Chrome, link: str, index: int) -> dict:
    """
    尝试爬取单篇文章的标题和摘要
    :return: 成功返回包含数据的字典，失败返回 None
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            driver.get(link)

            # === 核心反爬跳过逻辑 (参考你的需求) ===
            # 有些页面加载后需要运行此脚本才能显示内容或跳过隐形验证
            try:
                driver.execute_script("redirectNewLink()")
            except Exception:
                pass  # 如果当前页面没有这个函数，说明不需要或不是验证页，忽略

            # 等待页面元素加载 (标题)
            # 如果加载超时，可能是被验证码拦截了
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".wx-tit, h1"))
                )
            except Exception:
                # 如果没找到标题，尝试刷新并再次执行跳过逻辑
                logging.debug(f"Article {index}: 元素未加载，尝试刷新重试 (Attempt {attempt})")
                driver.refresh()
                time.sleep(1.5)
                try:
                    driver.execute_script("redirectNewLink()")
                except:
                    pass

            # === 再次检查验证码 ===
            if "拼图校验" in driver.page_source or "waf_verify" in driver.current_url:
                logging.warning(f"Article {index}: 触发验证码 (Attempt {attempt})")
                # 这里可以添加更复杂的等待或手动处理逻辑
                time.sleep(random.uniform(2, 5))
                # 如果是最后一次尝试依然失败，则跳过
                if attempt == MAX_RETRIES:
                    return None
                continue

            # === 数据提取 ===
            # 1. 提取标题
            title_ele = driver.find_element(By.CSS_SELECTOR, ".wx-tit")
            title = title_ele.text.strip()

            # 2. 提取摘要
            # 摘要可能有 'abstract-text' class，或者在 id 'ChDivSummary' 中
            abstract = ""
            try:
                # 尝试获取 .abstract-text
                abs_ele = driver.find_element(By.CSS_SELECTOR, ".abstract-text")
                abstract = abs_ele.text.strip()
            except Exception:
                try:
                    # 备用方案
                    abs_ele = driver.find_element(By.CSS_SELECTOR, "#ChDivSummary")
                    abstract = abs_ele.text.strip()
                except Exception:
                    abstract = "无摘要或提取失败"

            logging.info(f"Article {index} Success: {title[:15]}...")

            return {
                "title": title,
                "abstract": abstract,
                "url": link
            }

        except Exception as e:
            logging.error(f"Article {index} error on attempt {attempt}: {e}")
            time.sleep(random.uniform(1, 2))

    return None


def process_journal_year(name: str, year: str, links: list) -> None:
    """
    处理特定期刊特定年份的所有链接
    """
    # 结果保存路径
    save_base_name = os.path.join(DATA_DIR, f"{name}_{year}")
    ensure_directory(DATA_DIR)

    results = []
    skipped_links = []

    driver = None

    try:
        # 初始化驱动
        driver = load_chrome_driver()
        simulate_human_behavior(driver)

        total = len(links)
        logging.info(f"开始处理 {name} {year}, 共 {total} 篇文章")

        for idx, link in enumerate(links):
            # === 批次休息与重启 ===
            if idx > 0 and idx % BATCH_SIZE == 0:
                logging.info(f"已处理 {idx} 篇，休息并重启浏览器以规避反爬...")
                if driver:
                    driver.quit()
                time.sleep(5)  # 休息几秒
                driver = load_chrome_driver()
                simulate_human_behavior(driver)

            # === 执行爬取 ===
            data = attempt_scrape(driver, link, idx + 1)

            if data:
                results.append(data)
            else:
                skipped_links.append(link)

            # 随机休眠，模拟人类阅读间隔
            time.sleep(random.uniform(0.8, 1.5))

        # === 保存结果 ===
        if results:
            df = pd.DataFrame(results)

            # 保存 CSV (UTF-8-SIG 防止 Excel 打开乱码)
            csv_path = f"{save_base_name}.csv"
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')

            # 保存 JSON
            json_path = f"{save_base_name}.json"
            df.to_json(json_path, orient='records', force_ascii=False, indent=4)

            logging.info(f"保存完成: {csv_path} (共 {len(results)} 条)")

        if skipped_links:
            logging.warning(f"{name} {year} 有 {len(skipped_links)} 篇文章未成功爬取，已记录到日志。")
            # 可以选择将失败的链接保存到一个 txt 文件以便后续重试
            with open(f"{save_base_name}_failed.txt", "w", encoding="utf-8") as f:
                for sl in skipped_links:
                    f.write(sl + "\n")

    except Exception as e:
        logging.error(f"处理 {name} {year} 时发生致命错误: {e}")
    finally:
        if driver:
            driver.quit()


def process_txt_file(file_path: str) -> None:
    """
    读取 txt 文件并启动爬取流程
    """
    base_name = os.path.basename(file_path)
    try:
        # 文件名格式: 期刊名_年份.txt
        name_part, year_part = base_name.rsplit('_', 1)
        year = year_part.split('.')[0]
    except Exception as e:
        logging.error(f"文件名格式错误 {base_name}: {e}")
        return

    # 检查结果是否已存在，如果存在则跳过 (可选)
    expected_csv = os.path.join(DATA_DIR, f"{name_part}_{year}.csv")
    if os.path.exists(expected_csv):
        logging.info(f"结果文件 {expected_csv} 已存在，跳过。")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        links = [line.strip() for line in f if line.strip()]

    if not links:
        logging.warning(f"文件 {file_path} 为空")
        return

    process_journal_year(name_part, year, links)


def main() -> None:
    """主程序入口"""
    if not os.path.exists(LINK_DIR):
        logging.error(f"链接目录 {LINK_DIR} 不存在")
        return

    txt_files = [os.path.join(LINK_DIR, f) for f in os.listdir(LINK_DIR) if f.endswith('.txt')]

    if not txt_files:
        logging.warning("没有找到 txt 链接文件")
        return

    logging.info(f"发现 {len(txt_files)} 个任务文件，开始处理...")

    # 使用线程池并发处理不同年份/期刊
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_txt_file, file): file for file in txt_files}

        for future in as_completed(futures):
            file_path = futures[future]
            try:
                future.result()
            except Exception as e:
                logging.error(f"文件 {file_path} 处理过程中抛出异常: {e}")


if __name__ == '__main__':
    main()