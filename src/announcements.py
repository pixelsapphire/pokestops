from __future__ import annotations
from abc import abstractmethod
from bs4 import BeautifulSoup
from concurrent.futures import as_completed, Future, ThreadPoolExecutor
from data import __read_collection__
from data import *
from date import DateAndOrder
from log import log
from multiprocessing import cpu_count
from postprocess import clean_html
from selenium import webdriver
from selenium.common import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from sys import stdout
from threading import Lock
from tqdm import tqdm
from typing import override
from util import *


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

    def __eq__(self, other):
        return self.announcement_id == other.announcement_id

    def __hash__(self):
        return hash(self.announcement_id)

    @staticmethod
    def read_list(source: str, lines: dict[str, Line]) -> list[Announcement]:
        log(f'  Reading announcements data from {source}... ', end='')
        constructor = lambda *row: Announcement(
            row[0], row[1],
            DateAndOrder(date_string=row[2], string_format='y-m-d') if row[2] else None,
            DateAndOrder(date_string=row[3], string_format='y-m-d|indefinite') if row[3] else None,
            DateAndOrder(date_string=row[4], string_format='y-m-d') if row[4] else None,
            [lines.get(line, Line.dummy(line)) for line in row[5].split('&')] if row[5] else [])
        # warning caused by Pycharm issue PY-70668
        # noinspection PyTypeChecker
        return __read_collection__(source, [], constructor, list.append)


class ArticleScraper(ABC):
    def __init__(self, agency: str):
        self.driver: WebDriver = ArticleScraper.create_driver()
        self._agency: str = agency

    @staticmethod
    def create_driver() -> WebDriver:
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-images')
        options.add_argument('--disable-javascript')
        options.page_load_strategy = 'eager'
        return webdriver.Chrome(options=options)

    @staticmethod
    def postprocess_html(html: str) -> str:
        current_stage: str = html
        current_stage = re.sub(r'[^\-]color: ?#000000;?', 'color:white;', current_stage)
        current_stage = re.sub(r'</?strong>', '', current_stage)
        current_stage = re.sub(r'<span class="fontstyle\d+">\s*([^<>]+?)\s*</span>', lambda s: f' {s.group(1)}', current_stage)
        current_stage = current_stage.replace('„', '"').replace('”', '"')
        current_stage = clean_html(BeautifulSoup(current_stage, features='html.parser').prettify())
        current_stage = re.sub(r'"\n\s*(.+?)\n\s*"', lambda s: f'"{s.group(1)}"', current_stage)
        current_stage = re.sub(r'\(\n\s*(.+?)\n\s*\)', lambda s: f'({s.group(1)})', current_stage)
        current_stage = re.sub(r'\s?\u00A0\s?', '\u00A0', current_stage)
        return current_stage

    def open(self, url: str) -> None:
        self.driver.get(url)

    def close(self) -> None:
        self.driver.quit()

    @property
    def url(self) -> str:
        return self.driver.current_url

    @memoized
    def get_title(self) -> str:
        return self.driver.find_element(By.CSS_SELECTOR, '.container-xxl h1').text.replace('„', '"').replace('”', '"')

    @memoized
    def get_announcement_id(self) -> str:
        return f'{self._agency}-{self.url.split('/')[-1] if self.url.split('/')[-1] else self.url.split('/')[-2]}'

    @abstractmethod
    @memoized
    def get_dates(self) -> dict[str, DateAndOrder | None]:
        pass

    def get_date_from(self) -> DateAndOrder | None:
        return self.get_dates()['from']

    def get_date_to(self) -> DateAndOrder | None:
        return self.get_dates()['to']

    def get_date_published(self) -> DateAndOrder | None:
        return self.get_dates().get('published', None)

    @abstractmethod
    @memoized
    def get_lines(self) -> list[Line]:
        pass

    @abstractmethod
    @memoized
    def get_content(self) -> str:
        pass


class MPKArticleScraper(ArticleScraper):
    def __init__(self):
        super().__init__('mpk')

    @staticmethod
    def get_articles(browser: WebDriver, url: str) -> list[str]:
        browser.get(url)
        try:
            container: WebElement = browser.find_element(By.ID, 'main-content').find_element(By.CLASS_NAME, 'row')
            return list(map(lambda e: e.find_element(By.TAG_NAME, 'a').get_attribute('href'),
                            container.find_elements(By.CLASS_NAME, 'col-md-6')))
        except Exception as e:
            error(f'Error while fetching MPK announcements index: {type(e).__name__} - {e}')
            return []

    @override
    @memoized
    def get_dates(self) -> dict[str, DateAndOrder | None]:
        try:
            dates_str: str = self.driver.find_element(By.CSS_SELECTOR, '.container-xxl .black-box.mb-3.me-2').text
        except NoSuchElementException:
            dates_str: str = self.driver.find_element(By.CSS_SELECTOR, '.container-xxl .hr-date').text
        dates = list(map(lambda date: DateAndOrder(date_string=date, string_format='d.m.y'),
                         [date for date in dates_str.replace('Obowiązuje: ', '').split(' - ') if date]))
        if len(dates) == 1:
            dates.append(DateAndOrder.distant_future) if '-' in dates_str else dates.append(None)
        return {'from': dates[0], 'to': dates[1]}

    @override
    @memoized
    def get_lines(self) -> list[Line]:
        try:
            lines_str: str = self.driver.find_element(By.CSS_SELECTOR, '.container-xxl .green-box.mb-3').text
        except NoSuchElementException:
            lines_str: str = ''
        lines: list[Line] = sorted(map(Line.dummy, lines_str.replace('Dotyczy: ', '').split(', ')))
        if lines[0].number == 'Wszystkie linie':
            lines[0].number = 'all lines'
        return lines

    @override
    @memoized
    def get_content(self) -> str:
        content_container: WebElement = self.driver.find_element(By.CSS_SELECTOR, '.container-xxl .content')
        return ArticleScraper.postprocess_html(content_container.get_attribute('innerHTML'))


class ZTMArticleScraper(ArticleScraper):
    def __init__(self):
        super().__init__('ztm')

    @staticmethod
    def get_articles(browser: WebDriver, url: str) -> list[str]:
        browser.get(url)
        try:
            container: WebElement = browser.find_element(By.ID, 'main-content').find_element(By.CSS_SELECTOR, '.row.gy-4')
            return list(map(lambda e: e.find_element(By.TAG_NAME, 'a').get_attribute('href'),
                            container.find_elements(By.CLASS_NAME, 'col-lg-6')))
        except Exception as e:
            error(f'Error while fetching ZTM announcements index: {type(e).__name__} - {e}')
            return []

    @override
    @memoized
    def get_dates(self) -> dict[str, DateAndOrder | None]:
        dates_str: str = self.driver.find_element(By.CSS_SELECTOR, '.text--green.fw-medium').text
        dates = list(map(lambda date: DateAndOrder(date_string=date, string_format='d.m.y'),
                         [date for date in re.sub(r'Obowiązuje ?(od )?', '', dates_str).split(' - ') if date]))
        published: DateAndOrder | None = None
        if len(dates) == 1:
            dates.append(DateAndOrder.distant_future)
        elif len(dates) == 0:
            dates = [None, None]
            try:
                seo: WebElement = self.driver.find_element(By.CSS_SELECTOR,
                                                           'script[type="application/ld+json"].yoast-schema-graph')
                graph_entry: dict[str, Any] = json.loads(seo.get_attribute('innerHTML'))['@graph'][0]
                date_published: str = graph_entry['dateModified' if 'dateModified' in graph_entry else 'datePublished'][:10]
                published: DateAndOrder = DateAndOrder(date_string=date_published, string_format='y-m-d')
            except NoSuchElementException:
                pass
        return {'from': dates[0], 'to': dates[1], 'published': published}

    @override
    @memoized
    def get_lines(self) -> list[Line]:
        pattern: re.Pattern[str] = re.compile(r'[Ll]ini[a-z:]+\s+([a-z:]+\s+)*(T?\d+(,\s+T?\d+)*(\s+(i|oraz)\s+T?\d+)?)')
        line_numbers: set[str] = set()
        for mention in pattern.findall(self.get_title()) + pattern.findall(self.get_content()):
            line_numbers.update(re.findall(r'T?\d+', mention[1]))
        lines: list[Line] = sorted(map(Line.dummy, line_numbers))
        if len(lines) > 30:
            lines = lines[:20] + [Line.dummy(f'and {len(lines) - 20} more')]
        return lines

    @override
    @memoized
    def get_content(self) -> str:
        content_container: WebElement = self.driver.find_element(By.CSS_SELECTOR, '.container-xxl .content .col-12:not(.my-2)')
        return ArticleScraper.postprocess_html(content_container.get_attribute('innerHTML'))


def __fetch_article__(url: str, scrapper: type, announcements: list[Announcement], pbar: tqdm, mutex: Lock) -> None:
    browser: ArticleScraper = scrapper()
    with mutex:
        pbar.update(0.5)
    browser.open(url)
    try:
        announcement_id: str = browser.get_announcement_id()
        title: str = browser.get_title()
        date_from: DateAndOrder | None = browser.get_date_from()
        date_to: DateAndOrder | None = browser.get_date_to()
        date_published: DateAndOrder | None = browser.get_date_published()
        lines: list[Line] = browser.get_lines()
        content: str = browser.get_content()
        with mutex:
            announcements.append(Announcement(announcement_id, title, date_from,
                                              date_to, date_published, lines, content))
    except Exception as e:
        error(f'Error while processing announcement at {url}: {type(e).__name__} - {e}')
    finally:
        with mutex:
            pbar.update(0.5)


def fetch_announcements(first_update: bool, initial_db: Database) -> None:
    if not first_update:
        initial_db.report_old_data(Database.partial(announcements=Announcement.read_list(ref.rawdata_announcements, {})))
    clear_directory(ref.templates_path_announcements)

    pbar: tqdm = tqdm(total=70, desc='Fetching announcements...', unit='article', dynamic_ncols=True, file=stdout)
    mutex: Lock = Lock()

    browser: WebDriver = ArticleScraper.create_driver()
    pbar.update(1)
    mpk_article_urls: list[str] = MPKArticleScraper.get_articles(browser, ref.url_announcements_mpk)
    pbar.update(0.5)
    ztm_article_urls: list[str] = ZTMArticleScraper.get_articles(browser, ref.url_announcements_ztm_1)
    pbar.update(0.5)
    ztm_article_urls += ZTMArticleScraper.get_articles(browser, ref.url_announcements_ztm_2)
    pbar.update(0.5)
    ztm_article_urls += ZTMArticleScraper.get_articles(browser, ref.url_announcements_ztm_3)
    pbar.update(0.5)
    browser.quit()

    pbar.total = len(mpk_article_urls) + len(ztm_article_urls) + 3
    pbar.refresh()
    announcements: list[Announcement] = []
    with ThreadPoolExecutor(max_workers=cpu_count()) as executor:
        mpk_jobs: list[Future[None]] = [executor.submit(__fetch_article__, url, MPKArticleScraper, announcements, pbar, mutex)
                                        for url in mpk_article_urls]
        ztm_jobs: list[Future[None]] = [executor.submit(__fetch_article__, url, ZTMArticleScraper, announcements, pbar, mutex)
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

    initial_db.announcements = announcements
