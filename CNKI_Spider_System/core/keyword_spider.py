import os
import time
import json
import logging
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

class KeywordSpider:
    """
    关键词检索爬虫
    """

    def __init__(self, driver_path: str, headless: bool = False):
        self.driver_path = driver_path
        self.headless = headless
        self.driver = None
        self.wait = None
        self.logger = logging.getLogger(__name__)

    def init_browser(self):
        """初始化浏览器"""
        try:
            chrome_options = Options()
            if self.headless:
                chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            chrome_options.add_argument(f'--user-agent={user_agent}')

            service = Service(executable_path=self.driver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, 20)

            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.logger.info("浏览器初始化成功")

        except Exception as e:
            self.logger.error(f"浏览器初始化失败: {e}")
            raise

    def search_and_get_abstracts(self, keyword: str, max_results: int = 20) -> List[Dict]:
        """
        搜索论文并获取摘要信息
        """
        papers = []

        try:
            self.logger.info(f"开始搜索: {keyword}")

            # 直接访问知网搜索页面
            url = f'https://kns.cnki.net/kns8s/defaultresult/index?kw={keyword}'
            self.driver.get(url)
            time.sleep(3)

            # 设置每页显示50条
            self._set_page_size(50)

            # 获取论文链接
            paper_links = self._get_paper_links(max_results)
            self.logger.info(f"获取到 {len(paper_links)} 篇论文链接")

            # 逐个获取论文摘要
            for i, (title, link, year) in enumerate(paper_links):
                if len(papers) >= max_results:
                    break

                try:
                    self.logger.info(f"正在获取第 {i + 1} 篇论文摘要: {title}")
                    abstract = self._get_paper_abstract(link)

                    paper_info = {
                        'title': title,
                        'link': link,
                        'year': year,
                        'abstract': abstract,
                        'keyword': keyword
                    }
                    papers.append(paper_info)

                    # 延迟防止请求过快
                    time.sleep(2)

                except Exception as e:
                    self.logger.error(f"获取论文摘要失败: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"搜索过程中发生错误: {e}")

        return papers

    def _set_page_size(self, size: int):
        """设置每页显示数量"""
        try:
            per_page_div = self.wait.until(
                EC.element_to_be_clickable((By.ID, 'perPageDiv'))
            )
            per_page_div.click()
            time.sleep(1)

            page_size_option = self.driver.find_element(By.CSS_SELECTOR, f'li[data-val="{size}"] a')
            page_size_option.click()
            time.sleep(3)

        except Exception as e:
            self.logger.warning(f"设置每页显示数量失败: {e}")

    def _get_paper_links(self, max_results: int) -> List[tuple]:
        """获取论文链接列表"""
        links = []
        page_count = 0

        while len(links) < max_results and page_count < 10:
            try:
                # 等待页面加载
                time.sleep(2)

                # 获取页面源码
                page_source = self.driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')

                # 查找论文标题链接
                fz14_links = soup.select('.fz14')
                # 查找日期单元格
                date_cells = soup.select('.date')

                self.logger.info(f"第 {page_count + 1} 页找到 {len(fz14_links)} 个论文链接")

                # 遍历当前页面的所有搜索结果
                for link_tag, date_cell in zip(fz14_links, date_cells):
                    if link_tag.has_attr('href'):
                        date_text = date_cell.get_text(strip=True)
                        year = date_text.split('-')[0] if date_text else '未知'
                        title = link_tag.get_text(strip=True)
                        link = link_tag['href']

                        # 处理相对链接
                        if link and not link.startswith('http'):
                            link = 'https://kns.cnki.net' + link

                        links.append((title, link, year))

                        if len(links) >= max_results:
                            break

                # 如果当前页已经达到最大数量，退出循环
                if len(links) >= max_results:
                    break

                # 尝试翻到下一页
                if not self._go_to_next_page():
                    break

                page_count += 1

            except Exception as e:
                self.logger.error(f"获取论文链接时发生错误: {e}")
                break

        return links[:max_results]

    def _go_to_next_page(self) -> bool:
        """翻到下一页"""
        try:
            next_button = self.driver.find_element(By.ID, 'PageNext')
            if 'disabled' in next_button.get_attribute('class'):
                return False

            next_button.click()
            time.sleep(2)
            return True

        except Exception as e:
            self.logger.warning(f"翻页失败: {e}")
            return False

    def _get_paper_abstract(self, paper_link: str) -> str:
        """获取论文摘要"""
        try:
            # 在新标签页中打开论文详情页
            original_window = self.driver.current_window_handle
            self.driver.execute_script("window.open('');")
            self.driver.switch_to.window(self.driver.window_handles[-1])

            self.driver.get(paper_link)
            time.sleep(3)

            # 尝试多种方式获取摘要
            abstract = self._extract_abstract_from_page()

            # 关闭当前标签页并切换回原标签页
            self.driver.close()
            self.driver.switch_to.window(original_window)

            return abstract

        except Exception as e:
            self.logger.error(f"获取摘要时发生错误: {e}")
            # 确保切换回原标签页
            if len(self.driver.window_handles) > 1:
                self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
            return "获取摘要失败"

    def _extract_abstract_from_page(self) -> str:
        """从详情页提取摘要"""
        try:
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')

            # 尝试多种选择器获取摘要
            abstract_selectors = [
                '#ChDivSummary',
                '.abstract-text',
                '[name="ChDivSummary"]',
                '.row .abstract-text',
                '.abstract-content'
            ]

            for selector in abstract_selectors:
                abstract_elem = soup.select_one(selector)
                if abstract_elem:
                    abstract_text = abstract_elem.get_text(strip=True)
                    if abstract_text and len(abstract_text) > 10:
                        return abstract_text

            # 备用方法：查找包含"摘要"的文本
            abstract_label = soup.find(text=lambda text: text and '摘要' in text)
            if abstract_label:
                # 尝试获取摘要内容
                parent = abstract_label.parent
                if parent:
                    # 获取父元素的所有文本
                    full_text = parent.get_text()
                    # 使用正则表达式提取摘要
                    import re
                    match = re.search(r'摘要[：:]\s*(.+?)(?=\n|$|关键词|【)', full_text)
                    if match:
                        return match.group(1).strip()

            return "未找到摘要"

        except Exception as e:
            self.logger.error(f"提取摘要时发生错误: {e}")
            return "提取摘要失败"

    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            self.logger.info("浏览器已关闭")