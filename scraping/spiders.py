import re
from typing import Union, List

import requests
import scrapy
from scrapy.http.response.html import HtmlResponse
import urllib.parse

from scraping.xpath import Xpath
from scraping.webdriver import WebDriver
from secrets import web_scraping_api_key


class QuestionSpider(scrapy.Spider):
    name = 'questions'

    def __init__(self, start_urls: List[str], page_limit: int = None):
        """ Initialize webdriver """
        self.pages_scrapped = 0
        self.page_limit = page_limit
        self.start_urls = start_urls
        super().__init__()

    def start_requests(self):
        for url in self.start_urls:
            if google_cache_url := self.search_google_cache(url):
                proxy_url = self.url_through_proxy(google_cache_url)
                yield scrapy.Request(url=proxy_url, callback=self.parse)
            else:
                yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response: HtmlResponse) -> None:
        """ Parse URL """
        if self.page_limit and self.page_limit == self.pages_scrapped:
            return
        if 'https://api.webscrapingapi.com' in response.request.url:
            current_page_url = re.search(r'url=(http[s]*://.*)', response.request.url).group(1)
        else:
            current_page_url = response.request.url
        not_a_robot_button_xpath = '//' + Xpath.BUTTON_NOT_A_ROBOT
        not_a_robot_button = response.xpath(not_a_robot_button_xpath)
        if not_a_robot_button:
            driver = WebDriver(response.request.url)
            driver.press_button(not_a_robot_button_xpath)
            driver.solve_captcha(response)
            response = scrapy.Selector(text=driver.get_current_source())

        question_list = response.xpath('//' + Xpath.QUESTION_LIST)
        self.parse_question_list(question_list)
        self.pages_scrapped += 1
        try:
            next_page_url = self.get_next_page_url(response, current_page_url)
            if google_cache_url := self.search_google_cache(next_page_url):
                next_page_url = self.url_through_proxy(google_cache_url)
            next_page_request = scrapy.Request(next_page_url, callback=self.parse)
            yield next_page_request
        except LastPage:
            pass

    def parse_question_list(self, question_list: scrapy.Selector) -> None:
        """ Parse list of questions on page """
        for number_on_page, question in enumerate(question_list):
            parsed_question = self.parse_question(question)
            yield parsed_question

    def parse_question(self, question_selector: scrapy.Selector) -> dict:
        """ Parse single question """
        question_title = question_selector.xpath('.//' + Xpath.QUESTION_TITLE).get().strip()
        question_topic = question_selector.xpath('.//' + Xpath.QUESTION_TOPIC).get().strip()
        text_as_lines = question_selector.xpath(".//" + Xpath.QUESTION_TEXT).extract()
        question_text = '\n'.join(map(lambda s: s.strip(), text_as_lines))
        variants = {}
        for variant in question_selector.xpath(".//" + Xpath.QUESTION_ANSWER_VARIANTS):
            variant_letter = variant.xpath(".//" + Xpath.QUESTION_VARIANT_LETTER).get().strip(' .\n\t')
            variant_text = variant.xpath(".//" + Xpath.QUESTION_VARIANT_TEXT).get().strip()
            variants[variant_letter] = variant_text
        correct_answer = question_selector.xpath(".//" + Xpath.QUESTION_CORRECT_ANSWER_LETTER).get()
        correct_answer_comment_raw = question_selector.xpath(".//" + Xpath.QUESTION_CORRECT_ANSWER_COMMENT).extract()
        correct_answer_comment = '\n'.join((map(lambda s: s.strip(), correct_answer_comment_raw)))
        comments_number = question_selector.xpath(".//" + Xpath.QUESTION_NUMBER_OF_COMMENTS).get()

        return {
            'title': question_title,
            'topic': question_topic,
            'text': question_text,
            'variants': variants,
            'answer': correct_answer,
            'answer_comment': correct_answer_comment,
            'number_of_comments': comments_number
        }

    def search_google_cache(self, url: str) -> Union[str, None]:
        """ Search given url in Google cache. Return cached url if found, None if not found """
        cache_url = 'https://webcache.googleusercontent.com/search?q=cache:' + url
        proxy_url = self.url_through_proxy(cache_url)
        req = requests.get(proxy_url)
        if req.status_code == 200:
            return cache_url
        else:
            return None

    def url_through_proxy(self, url: str) -> str:
        """ Construct url for request through proxy """
        proxy_url = 'https://api.webscrapingapi.com/v1/?api_key=' + web_scraping_api_key + '&url=' + url
        return proxy_url

    def get_next_page_url(self, response: HtmlResponse, current_page_url: str = None) -> str:
        """ Find next page button and extract URL of next page. Concatenate it with domain name """
        next_page_button = response.xpath('//' + Xpath.BUTTON_NEXT_PAGE)
        if not next_page_button:
            raise LastPage
        else:
            next_page_relative_url = next_page_button.attrib['href']
            next_page_full_url = urllib.parse.urljoin(current_page_url, next_page_relative_url)
            return next_page_full_url


class LastPage(Exception):
    pass
