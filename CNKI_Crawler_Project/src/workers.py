import time
import os
import random
import logging
import pandas as pd
from PyQt5.QtCore import QThread, pyqtSignal
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

from .config import CHROME_DRIVER_PATH, LINK_DIR, RESULT_DIR


# 通用浏览器加载函数
def get_driver(headless=False):
    options = Options()
    if headless:
        options.add_argument('--headless')

    # === 关键反爬设置 ===
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    # 窗口最大化，防止元素折叠
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")

    service = Service(CHROME_DRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)

    # 移除 webdriver 特征
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    return driver


# 辅助函数：智能等待元素，支持人工过验证码
def wait_for_element_ignore_captcha(driver, by, value, timeout=120, log_signal=None):
    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            element = WebDriverWait(driver, 2).until(EC.presence_of_element_located((by, value)))
            return element
        except TimeoutException:
            current_url = driver.current_url
            if "waf" in current_url or "verify" in current_url:
                if log_signal:
                    log_signal.emit(
                        f"⚠️ 检测到验证码！请在浏览器中手动完成滑块验证... (剩余等待: {int(end_time - time.time())}秒)")
                time.sleep(3)
            else:
                if log_signal:
                    log_signal.emit(f"正在等待页面加载...({int(end_time - time.time())}s)")
                time.sleep(2)
    raise TimeoutException(f"在 {timeout} 秒内未找到元素: {value}，且用户未完成验证。")


# --- DS1: 关键词爬虫线程 ---
class KeywordWorker(QThread):
    log_signal = pyqtSignal(str)
    finish_signal = pyqtSignal(str)

    def __init__(self, keyword, count):
        super().__init__()
        self.keyword = keyword
        self.count = count

    def run(self):
        driver = None
        try:
            driver = get_driver(headless=False)
            self.log_signal.emit(f"开始关键词搜索: {self.keyword}")
            results = []

            url = f'https://kns.cnki.net/kns8s/defaultresult/index?kw={self.keyword}'
            driver.get(url)

            wait_for_element_ignore_captcha(driver, By.CLASS_NAME, "fz14", log_signal=self.log_signal)

            page = 0
            while len(results) < self.count and page < 5:
                rows = driver.find_elements(By.CSS_SELECTOR, ".fz14")
                dates = driver.find_elements(By.CSS_SELECTOR, ".date")

                for i in range(len(rows)):
                    if len(results) >= self.count: break
                    try:
                        title = rows[i].text.strip()
                        link = rows[i].get_attribute('href')
                        year = dates[i].text.strip().split('-')[0]
                        results.append({'title': title, 'link': link, 'year': year, 'abstract': '待获取'})
                    except:
                        continue

                if len(results) >= self.count: break

                try:
                    next_btn = driver.find_element(By.ID, 'PageNext')
                    next_btn.click()
                    time.sleep(3)
                    page += 1
                except:
                    break

            timestamp = time.strftime("%Y%m%d_%H%M%S")
            save_path = os.path.join(RESULT_DIR, f"{self.keyword}_{timestamp}.csv")
            pd.DataFrame(results).to_csv(save_path, index=False, encoding='utf-8-sig')
            self.finish_signal.emit(save_path)

        except Exception as e:
            self.log_signal.emit(f"错误: {str(e)}")
        finally:
            if driver:
                driver.quit()


# --- DS2: ISSN获取链接线程 (核心修复版) ---
class IssnLinkWorker(QThread):
    log_signal = pyqtSignal(str)
    finish_signal = pyqtSignal(str)

    def __init__(self, issn, start_year, end_year):
        super().__init__()
        self.issn = issn
        self.year_range = [start_year, end_year]

    def run(self):
        driver = None
        try:
            driver = get_driver(headless=False)
            self.log_signal.emit(f"正在检索期刊 ISSN: {self.issn}")

            driver.get('https://navi.cnki.net/')

            # 1. 智能等待
            try:
                search_dropdown = wait_for_element_ignore_captcha(
                    driver, By.ID, "txt_1_sel", timeout=120, log_signal=self.log_signal
                )
            except TimeoutException:
                self.log_signal.emit("❌ 错误：等待超时。")
                return

            self.log_signal.emit("✅ 页面加载成功，开始执行自动化操作...")

            # 2. 选择 ISSN
            search_dropdown.click()
            time.sleep(1)

            found_issn = False
            try:
                options = driver.find_elements(By.CSS_SELECTOR, "#txt_1_sel option")
                for opt in options:
                    if "ISSN" in opt.text:
                        opt.click()
                        found_issn = True
                        break
            except:
                pass

            if not found_issn:
                # 备用 XPath
                try:
                    driver.find_element(By.XPATH, "//option[contains(text(), 'ISSN')]").click()
                except:
                    self.log_signal.emit("❌ 无法选择 ISSN 选项")
                    return

            time.sleep(0.5)
            input_box = driver.find_element(By.ID, "txt_1_value1")
            input_box.clear()
            input_box.send_keys(self.issn)

            driver.find_element(By.ID, "btnSearch").click()
            time.sleep(2)

            # 3. 点击期刊结果
            try:
                first_journal = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".re_bookCover"))
                )
                first_journal.click()
            except:
                self.log_signal.emit("❌ 未找到期刊结果")
                return

            time.sleep(3)

            if len(driver.window_handles) > 1:
                driver.switch_to.window(driver.window_handles[-1])

            # 4. 获取期刊名 (增强版选择器)
            journal_name = self.issn
            try:
                # 尝试多个可能的位置
                selectors = [
                    ".journalTitle",
                    "h1.title",
                    "#journalTitle",
                    ".titbox h1"
                ]
                for sel in selectors:
                    try:
                        ele = driver.find_element(By.CSS_SELECTOR, sel)
                        if ele.text.strip():
                            journal_name = ele.text.strip()
                            break
                    except:
                        continue
            except:
                pass

            self.log_signal.emit(f"锁定期刊: {journal_name}")

            all_links = []

            # 5. 年份遍历
            for year in range(self.year_range[0], self.year_range[1] + 1):
                self.log_signal.emit(f"正在处理 {year} 年...")
                try:
                    year_id = f"{year}_Year_Issue"

                    try:
                        year_ele = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.ID, year_id))
                        )
                    except:
                        self.log_signal.emit(f"未找到 {year} 年数据")
                        continue

                    # 展开年份
                    try:
                        dt_ele = year_ele.find_element(By.TAG_NAME, "dt")
                        driver.execute_script("arguments[0].click();", dt_ele)
                        time.sleep(1)
                    except:
                        pass

                    issues = year_ele.find_elements(By.CSS_SELECTOR, "dd a")
                    num_issues = len(issues)
                    self.log_signal.emit(f"  - {year}年共有 {num_issues} 期")

                    for i in range(num_issues):
                        try:
                            # 重新获取元素
                            year_ele_refresh = driver.find_element(By.ID, year_id)
                            issues_refresh = year_ele_refresh.find_elements(By.CSS_SELECTOR, "dd a")

                            if i >= len(issues_refresh): break

                            issue_btn = issues_refresh[i]

                            # 获取这一期的名称用于日志 (e.g., No.01)
                            issue_name = issue_btn.text.strip()

                            # 点击具体某一期
                            driver.execute_script("arguments[0].click();", issue_btn)

                            # === 关键修正：等待内容加载 ===
                            # 点击后，右侧 #CataLogContent 会刷新，我们稍微等一下
                            time.sleep(2.5)

                            # === 关键修正：使用更强的链接提取逻辑 ===
                            current_issue_links = []

                            # 方法1：通过 XPath 查找所有包含 article/abstract 的链接
                            # 这是最稳健的，不管 CSS 类名怎么变
                            try:
                                xpath_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'article/abstract')]")
                                for l in xpath_links:
                                    href = l.get_attribute("href")
                                    if href and href not in current_issue_links:
                                        current_issue_links.append(href)
                            except:
                                pass

                            # 方法2：如果方法1没找到，尝试原来的 DS2 选择器
                            if not current_issue_links:
                                css_selectors = ["#CataLogContent a.name", ".name a", "td a.fz14"]
                                for sel in css_selectors:
                                    try:
                                        links = driver.find_elements(By.CSS_SELECTOR, sel)
                                        for l in links:
                                            href = l.get_attribute("href")
                                            if href and "article/abstract" in href and href not in current_issue_links:
                                                current_issue_links.append(href)
                                    except:
                                        pass

                            # 添加到总列表
                            for link in current_issue_links:
                                all_links.append(link)

                            self.log_signal.emit(
                                f"    > 第 {i + 1} 期 ({issue_name}): 抓取 {len(current_issue_links)} 条")

                            # 随机休眠
                            time.sleep(random.uniform(0.5, 1.5))

                        except Exception as e:
                            self.log_signal.emit(f"    > 第 {i + 1} 期异常: {e}")

                except Exception as e:
                    self.log_signal.emit(f"  - {year}年异常: {e}")

            # 6. 保存
            if all_links:
                # 清理文件名
                safe_name = "".join([c for c in journal_name if c.isalnum() or c in (' ', '-', '_', '.')])
                if not safe_name: safe_name = self.issn  # 如果还是获取不到名，用ISSN

                file_name = f"{safe_name}_{self.year_range[0]}-{self.year_range[1]}.txt"
                save_path = os.path.join(LINK_DIR, file_name)

                unique_links = list(set(all_links))
                with open(save_path, 'w', encoding='utf-8') as f:
                    for l in unique_links:
                        f.write(l + '\n')

                self.finish_signal.emit(save_path)
            else:
                self.log_signal.emit("⚠️ 未找到任何有效链接，请检查网页结构是否变化")

        except Exception as e:
            self.log_signal.emit(f"致命错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.log_signal.emit("任务结束，正在关闭浏览器...")
            if driver:
                driver.quit()


# --- DS3: 详情页爬取线程 (保持不变) ---
class DetailWorker(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finish_signal = pyqtSignal(str)

    def __init__(self, txt_path):
        super().__init__()
        self.txt_path = txt_path

    def run(self):
        driver = None
        try:
            with open(self.txt_path, 'r', encoding='utf-8') as f:
                links = [line.strip() for line in f if line.strip()]

            if not links:
                self.log_signal.emit("链接文件为空")
                return

            driver = get_driver(headless=False)
            results = []
            total = len(links)

            self.log_signal.emit(f"开始采集详情，共 {total} 篇")
            base_name = os.path.basename(self.txt_path).replace('.txt', '')

            for idx, link in enumerate(links):
                try:
                    driver.get(link)

                    try:
                        wait_for_element_ignore_captcha(
                            driver, By.CSS_SELECTOR, ".wx-tit, h1", timeout=8, log_signal=None
                        )
                    except TimeoutException:
                        self.log_signal.emit(f"[{idx + 1}] 加载超时，跳过")
                        continue

                    title = "未知"
                    abstract = "无摘要"

                    try:
                        title = driver.find_element(By.CSS_SELECTOR, ".wx-tit").text.strip()
                    except:
                        pass

                    try:
                        abstract = driver.find_element(By.CSS_SELECTOR, ".abstract-text").text.strip()
                    except:
                        try:
                            abstract = driver.find_element(By.CSS_SELECTOR, "#ChDivSummary").text.strip()
                        except:
                            pass

                    results.append({'title': title, 'abstract': abstract, 'link': link})
                    self.log_signal.emit(f"[{idx + 1}/{total}] {title[:10]}...")
                    self.progress_signal.emit(int((idx + 1) / total * 100))

                    time.sleep(random.uniform(1.0, 2.0))

                except Exception as e:
                    self.log_signal.emit(f"[{idx + 1}] 失败: {e}")

            save_path = os.path.join(RESULT_DIR, f"{base_name}_details.csv")
            pd.DataFrame(results).to_csv(save_path, index=False, encoding='utf-8-sig')
            self.finish_signal.emit(save_path)

        except Exception as e:
            self.log_signal.emit(f"任务出错: {e}")
        finally:
            if driver:
                driver.quit()