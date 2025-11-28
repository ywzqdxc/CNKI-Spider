import os
import time
import logging
from typing import List
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options


class JournalSpider:
    """
    期刊检索爬虫
    """

    def __init__(self, driver_path: str, headless: bool = False):
        self.driver_path = driver_path
        self.headless = headless
        self.driver = None
        self.logger = logging.getLogger(__name__)

    def init_browser(self):
        """初始化浏览器"""
        try:
            options = Options()
            if self.headless:
                options.add_argument('--headless')
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")

            user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            options.add_argument(f'--user-agent={user_agent}')

            service = Service(executable_path=self.driver_path)
            self.driver = webdriver.Chrome(service=service, options=options)

            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.logger.info("期刊爬虫浏览器初始化成功")

        except Exception as e:
            self.logger.error(f"期刊爬虫浏览器初始化失败: {e}")
            raise

    def is_valid_article_link(self, link: str) -> bool:
        """判断链接是否为有效的文章详情页链接"""
        if not link:
            return False

        valid_patterns = [
            'https://kns.cnki.net/kcms2/article/abstract',
            'http://kns.cnki.net/kcms2/article/abstract'
        ]

        return any(link.startswith(pattern) for pattern in valid_patterns)

    def process_journal(self, issn: str, year_range: List[int], max_results: int = 50) -> List[str]:
        """
        根据期刊ISSN检索期刊，并收集指定年份的文章链接
        """
        all_links = []

        try:
            self.driver.get('https://navi.cnki.net/')
            time.sleep(3)
            self.logger.info(f"正在检索期刊 ISSN: {issn}，年份范围: {year_range[0]}-{year_range[1]}")

            # 选择检索方式为ISSN
            select_element = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.ID, "txt_1_sel"))
            )
            select_element.click()
            time.sleep(1)

            # 选择ISSN选项
            option_elements = self.driver.find_elements(By.CSS_SELECTOR, "#txt_1_sel option")
            for option in option_elements:
                if "ISSN" in option.text:
                    option.click()
                    break
            time.sleep(1)

            # 输入ISSN
            input_element = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.ID, "txt_1_value1"))
            )
            input_element.clear()
            input_element.send_keys(issn)

            # 点击搜索按钮
            button_element = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.ID, "btnSearch"))
            )
            button_element.click()
            time.sleep(3)

            # 等待页面加载完成并点击第一个期刊
            first_journal = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".re_bookCover"))
            )
            first_journal.click()

            time.sleep(3)
            # 切换到新打开的窗口
            if len(self.driver.window_handles) > 1:
                self.driver.switch_to.window(self.driver.window_handles[-1])

            # 获取期刊名称
            journal_name = issn
            try:
                journal_name_element = WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".journalTitle, .title"))
                )
                journal_name = journal_name_element.text.strip()
                journal_name = "".join(c for c in journal_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                self.logger.info(f"获取到期刊名称: {journal_name}")
            except Exception as e:
                self.logger.warning(f"无法获取期刊名称，使用ISSN作为文件名: {e}")

            # 遍历指定年份，收集期刊文章链接
            for year in range(year_range[0], year_range[1] + 1):
                if len(all_links) >= max_results:
                    break

                self.logger.info(f"正在检索 {journal_name} {year} 年的期刊链接")

                try:
                    year_id = f"{year}_Year_Issue"
                    year_element = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.ID, year_id))
                    )

                    # 展开年份下拉
                    dt_element = WebDriverWait(year_element, 10).until(
                        EC.element_to_be_clickable((By.TAG_NAME, "dt"))
                    )
                    self.driver.execute_script("arguments[0].click();", dt_element)
                    time.sleep(1)

                    issue_elements = year_element.find_elements(By.CSS_SELECTOR, "dd a")
                    year_links = []

                    for i in range(len(issue_elements)):
                        if len(all_links) >= max_results:
                            break

                        try:
                            # 重新获取元素避免stale element
                            year_element_refreshed = self.driver.find_element(By.ID, year_id)
                            issue_elements_refreshed = year_element_refreshed.find_elements(By.CSS_SELECTOR, "dd a")

                            if i >= len(issue_elements_refreshed):
                                break

                            issue_element = issue_elements_refreshed[i]
                            WebDriverWait(self.driver, 10).until(
                                EC.element_to_be_clickable(issue_element)
                            )
                            self.driver.execute_script("arguments[0].click();", issue_element)
                            time.sleep(2)

                            # 获取文章链接
                            link_elements = WebDriverWait(self.driver, 10).until(
                                EC.presence_of_all_elements_located(
                                    (By.CSS_SELECTOR, "#CataLogContent a.name, .row a, .list-item a, a.fz14"))
                            )

                            # 过滤链接，只保留有效的文章详情页链接
                            valid_links = []
                            for link_element in link_elements:
                                link = link_element.get_attribute("href")
                                if self.is_valid_article_link(link) and link not in valid_links:
                                    valid_links.append(link)
                                    year_links.append(link)

                            self.logger.info(f"第 {i + 1} 期找到 {len(valid_links)} 个有效文章链接")

                        except Exception as e:
                            self.logger.warning(f"处理第 {i + 1} 期时发生错误: {e}")
                            continue

                    all_links.extend(year_links[:max_results - len(all_links)])

                except Exception as e:
                    self.logger.error(f"处理 {journal_name} {year} 年时发生错误: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"处理期刊 {issn} 时发生错误: {e}", exc_info=True)

        return all_links[:max_results]

    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            self.logger.info("期刊爬虫浏览器已关闭")