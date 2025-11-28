import logging
from typing import List, Dict


class UnifiedSpider:
    """
    统一爬虫引擎，整合三个核心功能
    """

    def __init__(self, driver_path: str, headless: bool = False):
        self.driver_path = driver_path
        self.headless = headless

        # 延迟导入以避免循环依赖
        from core.abstract_spider import AbstractSpider
        from core.keyword_spider import KeywordSpider
        from core.journal_spider import JournalSpider

        self.keyword_spider = None
        self.journal_spider = None
        self.abstract_spider = AbstractSpider(driver_path, headless)
        self.logger = logging.getLogger(__name__)

    def search_by_keyword(self, keyword: str, max_results: int = 50) -> List[Dict]:
        """关键词检索入口"""
        try:
            from core.keyword_spider import KeywordSpider
            self.keyword_spider = KeywordSpider(self.driver_path, self.headless)
            self.keyword_spider.init_browser()
            results = self.keyword_spider.search_and_get_abstracts(keyword, max_results)
            return results
        except Exception as e:
            self.logger.error(f"关键词检索失败: {e}")
            return []
        finally:
            if self.keyword_spider:
                self.keyword_spider.close()

    def search_by_issn(self, issn: str, year_range: List[int], max_results: int = 50) -> List[Dict]:
        """期刊检索入口"""
        try:
            # 获取文献链接
            from core.journal_spider import JournalSpider
            self.journal_spider = JournalSpider(self.driver_path, self.headless)
            self.journal_spider.init_browser()
            links = self.journal_spider.process_journal(issn, year_range, max_results)

            # 批量获取摘要
            results = self.abstract_spider.batch_process_links(links)
            return results
        except Exception as e:
            self.logger.error(f"期刊检索失败: {e}")
            return []
        finally:
            if self.journal_spider:
                self.journal_spider.close()

    def process_existing_links(self, links: List[str]) -> List[Dict]:
        """处理现有链接"""
        return self.abstract_spider.batch_process_links(links)