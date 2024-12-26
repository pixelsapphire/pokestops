from __future__ import annotations
from bs4 import BeautifulSoup
from concurrent.futures import as_completed, Future, ThreadPoolExecutor
from data import __read_collection__
from data import *
from multiprocessing import cpu_count
from postprocess import clean_html
from selenium import webdriver
from selenium.common import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from threading import Lock
from tqdm import tqdm
from util import *

__mutex__: Lock = Lock()


class Announcement(JsonSerializable):
    def __init__(self, announcement_id: str, title: str,
                 date_from: DateAndOrder | None, date_to: DateAndOrder | None, date_published: DateAndOrder | None,
                 lines: list[Line], content: str | None = None):
        self.announcement_id: str = announcement_id
        self.title: str = title
        self.date_from: DateAndOrder | None = date_from
        self.date_to: DateAndOrder | None = date_to
        self.date_published: DateAndOrder | None = date_published
        self.lines: list[Line] = lines
        self.content: str | None = content

    @staticmethod
    def read_list(source: str, lines: dict[str, Line]) -> list[Announcement]:
        print(f'  Reading announcements data from {source}... ', end='')
        constructor = lambda *row: Announcement(
            row[0], row[1],
            DateAndOrder(date_string=row[2], string_format='y-m-d') if row[2] else None,
            DateAndOrder(date_string=row[3], string_format='y-m-d|indefinite') if row[3] else None,
            DateAndOrder(date_string=row[4], string_format='y-m-d') if row[4] else None,
            [lines.get(line, Line.dummy(line)) for line in row[5].split('&')] if row[5] else [])
        # warning caused by Pycharm issue PY-70668
        # noinspection PyTypeChecker
        return __read_collection__(source, [], constructor, list.append)


def create_driver() -> WebDriver:
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-images')
    options.add_argument('--disable-javascript')
    options.page_load_strategy = 'eager'
    return webdriver.Chrome(options=options)


def postprocess_html(html: str) -> str:
    current_stage: str = html
    current_stage = re.sub(r'[^\-]color: ?#000000;?', 'color:white;', current_stage)
    current_stage = re.sub(r'</?strong>', '', current_stage)
    current_stage = re.sub(r'<span class="fontstyle\d+">\s*([^<>]+?)\s*</span>', lambda s: f' {s.group(1)}', current_stage)
    current_stage = current_stage.replace('„', '"').replace('”', '"')
    current_stage = clean_html(BeautifulSoup(current_stage, features='html.parser').prettify())
    current_stage = re.sub(r'"\n\s*(.+?)\n\s*"', lambda s: f'"{s.group(1)}"', current_stage)
    current_stage = re.sub(r'\(\n\s*(.+?)\n\s*\)', lambda s: f'({s.group(1)})', current_stage)
    return current_stage


def fetch_mpk_article(url: str, announcements: list[Announcement], pbar: tqdm) -> None:
    browser: WebDriver = create_driver()
    with __mutex__:
        pbar.update(0.5)
    browser.get(url)
    announcement_id: str = f'mpk-{url.split('/')[-1] if url.split('/')[-1] else url.split('/')[-2]}'

    title: str = browser.find_element(By.CSS_SELECTOR, '.container-xxl h1').text.replace('„', '"').replace('”', '"')

    try:
        dates_str: str = browser.find_element(By.CSS_SELECTOR, '.container-xxl .black-box.mb-3.me-2').text
    except NoSuchElementException:
        dates_str: str = browser.find_element(By.CSS_SELECTOR, '.container-xxl .hr-date').text
    dates = list(map(lambda date: DateAndOrder(date_string=date, string_format='d.m.y'),
                     [date for date in dates_str.replace('Obowiązuje: ', '').split(' - ') if date]))
    if len(dates) == 1:
        dates.append(DateAndOrder.distant_future) if '-' in dates_str else dates.append(None)

    try:
        lines_str: str = browser.find_element(By.CSS_SELECTOR, '.container-xxl .green-box.mb-3').text
    except NoSuchElementException:
        lines_str: str = ''
    lines: list[Line] = sorted(map(Line.dummy, lines_str.replace('Dotyczy: ', '').split(', ')))
    if lines[0].number == 'Wszystkie linie':
        lines[0].number = 'all lines'

    content_container: WebElement = browser.find_element(By.CSS_SELECTOR, '.container-xxl .content')
    content: str = postprocess_html(content_container.get_attribute('innerHTML'))
    browser.quit()

    with __mutex__:
        announcements.append(Announcement(announcement_id, title, dates[0], dates[1], None, lines, content))
        pbar.update(0.5)


def fetch_ztm_article(url: str, announcements: list[Announcement], pbar: tqdm) -> None:
    browser: WebDriver = create_driver()
    with __mutex__:
        pbar.update(0.5)
    browser.get(url)
    announcement_id: str = f'ztm-{url.split('/')[-1] if url.split('/')[-1] else url.split('/')[-2]}'

    title: str = browser.find_element(By.CSS_SELECTOR, '.container-xxl h1').text.replace('„', '"').replace('”', '"')

    dates_str: str = browser.find_element(By.CSS_SELECTOR, '.text--green.fw-medium').text
    dates = list(map(lambda date: DateAndOrder(date_string=date, string_format='d.m.y'),
                     [date for date in re.sub(r'Obowiązuje ?(od )?', '', dates_str).split(' - ') if date]))
    published: DateAndOrder | None = None
    if len(dates) == 1:
        dates.append(DateAndOrder.distant_future)
    elif len(dates) == 0:
        dates = [None, None]
        try:
            seo: WebElement = browser.find_element(By.CSS_SELECTOR, 'script[type="application/ld+json"].yoast-schema-graph')
            date_modified: str = json.loads(seo.get_attribute('innerHTML'))['@graph'][0]['dateModified'][:10]
            published: DateAndOrder = DateAndOrder(date_string=date_modified, string_format='y-m-d')
        except NoSuchElementException:
            pass

    content_container: WebElement = browser.find_element(By.CSS_SELECTOR, '.container-xxl .content .col-12:not(.my-2)')
    content: str = postprocess_html(content_container.get_attribute('innerHTML'))
    browser.quit()

    with __mutex__:
        announcements.append(Announcement(announcement_id, title, dates[0], dates[1], published, [], content))
        pbar.update(0.5)


def get_articles_mpk(browser: WebDriver) -> list[str]:
    browser.get(ref.url_announcements_mpk)
    container: WebElement = browser.find_element(By.ID, 'main-content').find_element(By.CLASS_NAME, 'row')
    return list(map(lambda e: e.find_element(By.TAG_NAME, 'a').get_attribute('href'),
                    container.find_elements(By.CLASS_NAME, 'col-md-6')))


def get_articles_ztm(browser: WebDriver, url: str) -> list[str]:
    browser.get(url)
    container: WebElement = browser.find_element(By.ID, 'main-content').find_element(By.CSS_SELECTOR, '.row.gy-4')
    return list(map(lambda e: e.find_element(By.TAG_NAME, 'a').get_attribute('href'),
                    container.find_elements(By.CLASS_NAME, 'col-lg-6')))


def fetch_announcements() -> None:
    pbar: tqdm = tqdm(total=70, desc='Fetching announcements...', unit='article', dynamic_ncols=True, file=sys.stdout)

    browser: WebDriver = create_driver()
    pbar.update(1)
    mpk_article_urls: list[str] = get_articles_mpk(browser)
    pbar.update(0.5)
    ztm_article_urls: list[str] = get_articles_ztm(browser, ref.url_announcements_ztm_1)
    pbar.update(0.5)
    ztm_article_urls += get_articles_ztm(browser, ref.url_announcements_ztm_2)
    pbar.update(0.5)
    ztm_article_urls += get_articles_ztm(browser, ref.url_announcements_ztm_3)
    pbar.update(0.5)
    browser.quit()

    pbar.total = len(mpk_article_urls) + len(ztm_article_urls) + 3
    pbar.refresh()
    announcements: list[Announcement] = []
    with ThreadPoolExecutor(max_workers=cpu_count()) as executor:
        mpk_jobs: list[Future[None]] = [executor.submit(fetch_mpk_article, url, announcements, pbar)
                                        for url in mpk_article_urls]
        ztm_jobs: list[Future[None]] = [executor.submit(fetch_ztm_article, url, announcements, pbar)
                                        for url in ztm_article_urls]
        for future in as_completed(mpk_jobs + ztm_jobs):
            future.result()
    announcements.sort(key=lambda a: (coalesce(a.date_from, a.date_published), a.date_to, a.announcement_id), reverse=True)

    header: str = 'announcement_id,title,date_from,date_to,date_published,lines'
    with open(prepare_file(ref.rawdata_announcements, f'{header}\n', True), 'a') as file:
        for announcement in announcements:
            file.write(f'{announcement.announcement_id},"{announcement.title.replace('"', '\"')}",'
                       f'{coalesce(maybe(announcement.date_from, DateAndOrder.format, 'y-m-d'), '')},'
                       f'{coalesce(maybe(announcement.date_to, DateAndOrder.format, 'y-m-d|indefinite'), '')},'
                       f'{coalesce(maybe(announcement.date_published, DateAndOrder.format, 'y-m-d'), '')},'
                       f'{'&'.join(line.number for line in announcement.lines)}\n')
            with open(prepare_file(f'{ref.templates_path_announcements}/{announcement.announcement_id}.jinja'), 'w') as article:
                article.write(announcement.content)
