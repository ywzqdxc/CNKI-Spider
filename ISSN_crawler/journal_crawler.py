import logging
import os
import time
from typing import List

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options

# 配置
DEBUG = True
CHROME_DRIVER_PATH = r'C:\Program Files\Google\Chrome\Application\chromedriver.exe'
CHROME_BINARY_PATH = r'C:\Program Files\Google\Chrome\Application\chrome.exe'  # 请根据实际情况修改
SAVE_DIR = 'saves'
LINK_DIR = 'links'
YEAR_RANGE = [2024, 2024]

# 配置日志记录
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def ensure_directory_exists(directory: str) -> None:
    """
    确保指定目录存在，若不存在则创建。
    """
    if not os.path.exists(directory):
        os.makedirs(directory)
        logging.debug(f"目录 {directory} 创建成功。")
    else:
        logging.debug(f"目录 {directory} 已存在。")


def load_chrome_driver() -> webdriver.Chrome:
    """
    加载ChromeDriver，使用已安装的驱动避免网络请求。
    """
    try:
        # 配置 Chrome 选项
        options = Options()

        # 添加反检测选项
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        # 如果知道 Chrome 安装路径，可以指定
        if os.path.exists(CHROME_BINARY_PATH):
            options.binary_location = CHROME_BINARY_PATH

        # 其他常用选项
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")

        # 创建服务
        service = Service(CHROME_DRIVER_PATH)

        # 创建驱动实例
        driver = webdriver.Chrome(service=service, options=options)

        # 执行脚本来隐藏自动化特征
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

        return driver

    except Exception as e:
        logging.error(f"创建 Chrome 驱动失败: {e}")
        raise


def is_valid_article_link(link: str) -> bool:
    """
    判断链接是否为有效的文章详情页链接。
    只保留 kns.cnki.net/kcms2/article/abstract 开头的链接。
    """
    if not link:
        return False

    # 过滤条件：只保留文章详情页链接
    valid_patterns = [
        'https://kns.cnki.net/kcms2/article/abstract',
        'http://kns.cnki.net/kcms2/article/abstract'
    ]

    return any(link.startswith(pattern) for pattern in valid_patterns)


def process_journal(issn: str, year_range: List[int]) -> None:
    """
    根据期刊ISSN检索期刊，并收集指定年份的文章链接，将链接保存到文件中。

    :param issn: 期刊 ISSN
    :param year_range: [起始年份, 结束年份]
    """
    driver = load_chrome_driver()
    try:
        driver.get('https://navi.cnki.net/')
        time.sleep(3)
        logging.info(f"正在检索期刊 ISSN: {issn}，年份范围: {year_range[0]}-{year_range[1]}")

        # 选择检索方式为ISSN
        select_element = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, "txt_1_sel"))
        )
        select_element.click()
        time.sleep(1)

        # 选择ISSN选项
        option_elements = driver.find_elements(By.CSS_SELECTOR, "#txt_1_sel option")
        for option in option_elements:
            if "ISSN" in option.text:
                option.click()
                break
        time.sleep(1)

        # 输入ISSN
        input_element = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, "txt_1_value1"))
        )
        input_element.clear()
        input_element.send_keys(issn)

        # 点击搜索按钮
        button_element = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, "btnSearch"))
        )
        button_element.click()
        time.sleep(3)

        # 等待页面加载完成并点击第一个期刊
        first_journal = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".re_bookCover"))
        )
        first_journal.click()

        time.sleep(3)
        # 切换到新打开的窗口
        if len(driver.window_handles) > 1:
            driver.switch_to.window(driver.window_handles[-1])

        # 获取期刊名称用于文件名
        journal_name = issn
        try:
            journal_name_element = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".journalTitle, .title"))
            )
            journal_name = journal_name_element.text.strip()
            # 清理文件名中的非法字符
            journal_name = "".join(c for c in journal_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            logging.info(f"获取到期刊名称: {journal_name}")
        except Exception as e:
            logging.warning(f"无法获取期刊名称，使用ISSN作为文件名: {e}")

        # 遍历指定年份，收集期刊文章链接
        for year in range(year_range[0], year_range[1] + 1):
            logging.info(f"正在检索 {journal_name} {year} 年的期刊链接")

            try:
                year_id = f"{year}_Year_Issue"
                year_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, year_id))
                )

                # 展开年份下拉
                dt_element = WebDriverWait(year_element, 10).until(
                    EC.element_to_be_clickable((By.TAG_NAME, "dt"))
                )
                driver.execute_script("arguments[0].click();", dt_element)
                time.sleep(1)

                issue_elements = year_element.find_elements(By.CSS_SELECTOR, "dd a")
                all_links: List[str] = []

                for i in range(len(issue_elements)):
                    try:
                        # 重新获取元素避免stale element
                        year_element_refreshed = driver.find_element(By.ID, year_id)
                        issue_elements_refreshed = year_element_refreshed.find_elements(By.CSS_SELECTOR, "dd a")

                        if i >= len(issue_elements_refreshed):
                            break

                        issue_element = issue_elements_refreshed[i]
                        WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable(issue_element)
                        )
                        driver.execute_script("arguments[0].click();", issue_element)
                        time.sleep(2)

                        # 获取文章链接 - 改进的选择器
                        link_elements = WebDriverWait(driver, 10).until(
                            EC.presence_of_all_elements_located(
                                (By.CSS_SELECTOR, "#CataLogContent a.name, .row a, .list-item a, a.fz14"))
                        )

                        # 过滤链接，只保留有效的文章详情页链接
                        valid_links = []
                        for link_element in link_elements:
                            link = link_element.get_attribute("href")
                            if is_valid_article_link(link) and link not in valid_links:
                                valid_links.append(link)
                                all_links.append(link)

                        logging.info(f"第 {i + 1} 期找到 {len(valid_links)} 个有效文章链接")

                    except Exception as e:
                        logging.warning(f"处理第 {i + 1} 期时发生错误: {e}")
                        continue

                # 去重并保存链接到文件
                if all_links:
                    # 去重
                    unique_links = list(set(all_links))
                    output_file = os.path.join(LINK_DIR, f"{journal_name}_{year}.txt")
                    with open(output_file, 'w', encoding='utf-8') as f:
                        for link in unique_links:
                            f.write(link + '\n')
                    logging.info(f"保存 {len(unique_links)} 个唯一链接到文件: {output_file}")
                else:
                    logging.warning(f"{journal_name} {year} 年未找到任何有效文章链接")

            except Exception as e:
                logging.error(f"处理 {journal_name} {year} 年时发生错误: {e}")
                continue

    except Exception as e:
        logging.error(f"处理期刊 {issn} 时发生错误: {e}", exc_info=True)
    finally:
        driver.quit()
        logging.debug("驱动已关闭。")


def main() -> None:
    """
    主函数：确保目录存在，并处理指定ISSN的期刊。
    """
    ensure_directory_exists(SAVE_DIR)
    ensure_directory_exists(LINK_DIR)

    # 直接使用ISSN号0577-9154进行爬取
    issn = "0577-9154"
    logging.info(f"开始爬取期刊 ISSN: {issn}")
    process_journal(issn, YEAR_RANGE)
    logging.info("爬取完成")


if __name__ == "__main__":
    main()