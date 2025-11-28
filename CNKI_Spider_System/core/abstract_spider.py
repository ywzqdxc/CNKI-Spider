import os
import random
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

class AbstractSpider:
    """
    摘要提取爬虫
    """

    def __init__(self, driver_path: str, headless: bool = False, max_retries: int = 3):
        self.driver_path = driver_path
        self.headless = headless
        self.max_retries = max_retries
        self.logger = logging.getLogger(__name__)

    def load_chrome_driver(self) -> webdriver.Chrome:
        """加载防检测的 Chrome 驱动"""
        options = Options()
        service = Service(self.driver_path)

        if self.headless:
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-images')

        # 反爬虫检测配置
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1920,1080")

        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        options.add_argument(f'--user-agent={user_agent}')

        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        return driver

    def simulate_human_behavior(self, driver: webdriver.Chrome) -> None:
        """模拟人类行为（闲逛），降低触发验证码的概率"""
        self.logger.info("正在进行人类行为模拟(闲逛)...")
        try:
            # 1. 访问首页
            driver.get('https://kns.cnki.net/kns8s/defaultresult/index')
            time.sleep(random.uniform(1, 2))

            # 2. 模拟一次搜索
            driver.get('https://kns.cnki.net/kns8s/defaultresult/index?kw=经济')
            time.sleep(random.uniform(1.5, 3))

            # 3. 模拟进入一个页面并刷新
            test_url = 'https://kns.cnki.net/kcms2/article/abstract?v=random_check'
            driver.get(test_url)
            for _ in range(2):
                driver.refresh()
                time.sleep(random.uniform(0.5, 1.0))

        except Exception as e:
            self.logger.warning(f"闲逛模拟中出现非致命错误: {e}")

    def clean_title_text(self, raw_text: str) -> str:
        """清洗标题文本"""
        if not raw_text:
            return ""
        return raw_text.split('\n')[0].strip()

    def attempt_scrape(self, driver: webdriver.Chrome, link: str, index: int) -> dict:
        """尝试爬取单篇文章的标题和摘要"""
        for attempt in range(1, self.max_retries + 1):
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
                    self.logger.warning(f"Article {index}: 触发验证码 (Attempt {attempt})")
                    time.sleep(random.uniform(3, 5))
                    if attempt == self.max_retries:
                        return None
                    continue

                # === 1. 提取并清洗标题 ===
                title_ele = driver.find_element(By.CSS_SELECTOR, ".wx-tit")
                raw_title = title_ele.text
                clean_title = self.clean_title_text(raw_title)

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

                self.logger.info(f"Article {index} Success: {clean_title[:15]}...")

                # === 返回结果 ===
                return {
                    "title": clean_title,
                    "abstract": abstract,
                    "link": link
                }

            except Exception as e:
                self.logger.error(f"Article {index} error on attempt {attempt}: {e}")
                time.sleep(random.uniform(1, 2))

        return None

    def batch_process_links(self, links: list, batch_size: int = 30) -> list:
        """批量处理链接"""
        results = []
        skipped_links = []

        driver = None

        try:
            driver = self.load_chrome_driver()
            self.simulate_human_behavior(driver)

            self.logger.info(f"开始处理 {len(links)} 篇文章")

            for idx, link in enumerate(links):
                # 批次重启逻辑
                if idx > 0 and idx % batch_size == 0:
                    self.logger.info(f"已处理 {idx} 篇，重启浏览器以刷新环境...")
                    if driver:
                        driver.quit()
                    time.sleep(5)
                    driver = self.load_chrome_driver()
                    self.simulate_human_behavior(driver)

                # 执行爬取
                data = self.attempt_scrape(driver, link, idx + 1)

                if data:
                    results.append(data)
                else:
                    skipped_links.append(link)

                time.sleep(random.uniform(0.8, 1.5))

        except Exception as e:
            self.logger.error(f"批量处理链接时发生错误: {e}")
        finally:
            if driver:
                driver.quit()

        return results