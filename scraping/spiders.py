import base64
from io import BytesIO
from time import sleep
from typing import Tuple, Dict

import scrapy
from scrapy import Selector
from scrapy.http.response.html import HtmlResponse
from selenium import webdriver
import selenium.common.exceptions as selenium_exceptions
import urllib.parse
from PIL import Image
from selenium.webdriver.common.by import By

from constants import RETRY_NUMBER_PER_PAGE
from scraping.xpath import Xpath
from scraping.captcha import CaptchaSolver


class QuestionSpider(scrapy.Spider):
    name = 'questions'
    # start_urls = ['https://www.examtopics.com/exams/amazon/aws-certified-solutions-architect-associate-saa-c02/view/']
    start_urls = ['https://www.examtopics.com/exams/microsoft/70-332/view/2']

    def __init__(self, page_limit: int = None):
        """ Initialize webdriver """
        self.driver = webdriver.Firefox()
        self.pages_scrapped = 0
        self.page_limit = page_limit
        super().__init__()

    def __del__(self):
        """ Close webdriver """
        self.driver.close()

    def parse(self, response: HtmlResponse) -> None:
        """ Parse URL """
        if self.page_limit and self.page_limit == self.pages_scrapped:
            return
        self.driver.get(response.request.url)
        current_url = response.request.url
        sleep(1)
        not_a_robot_button_xpath = '//' + Xpath.BUTTON_NOT_A_ROBOT
        not_a_robot_button = response.xpath(not_a_robot_button_xpath)
        if not_a_robot_button:
            self.press_button(not_a_robot_button_xpath)
            self.solve_captcha(response)
            response = scrapy.Selector(text=self.driver.page_source)
        self.close_last_page_disclaimer()

        question_list = response.xpath('//' + Xpath.QUESTION_LIST)
        for number_on_page, question in enumerate(question_list):
            parsed_question = self.parse_question(question)
            yield parsed_question
        try:
            self.pages_scrapped += 1
            next_page_relative_url = self.get_next_page(response)
            next_page_full_url = urllib.parse.urljoin(current_url, next_page_relative_url)
            next_page_request = scrapy.Request(next_page_full_url, callback=self.parse)
            yield next_page_request
        except LastPage:
            pass

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

    def press_reveal_solution(self, number_on_page: int) -> None:
        """ Press "Reveal Solution" button for the question with given number """
        xpath = f'//{Xpath.QUESTION_LIST}[{number_on_page + 1}]/{Xpath.BUTTON_REVEAL_SOLUTION}'
        self.press_button(xpath)

    def close_last_page_disclaimer(self) -> None:
        """ Close disclaimer window on the last page """
        xpath = f'//{Xpath.BUTTON_LAST_PAGE_DISCLAIMER}'
        try:
            button = self.driver.find_element_by_xpath(xpath)
            self.press_button(button)
        except selenium_exceptions.NoSuchElementException:
            pass

    def get_next_page(self, response: HtmlResponse) -> str:
        next_page_button = response.xpath('//' + Xpath.BUTTON_NEXT_PAGE)
        if not next_page_button:
            raise LastPage
        else:
            return next_page_button.attrib['href']

    def solve_captcha(self, response: HtmlResponse) -> None:
        """ Solve captcha """
        retries = 0
        try:
            while captcha := self.driver.find_element_by_xpath(f'//{Xpath.CAPTCHA_FRAME}'):
                captcha_container = self.driver.find_element_by_xpath(f'//{Xpath.CAPTCHA_CONTAINER}')
                captcha_location = captcha_container.location
                try:
                    # captcha = self.driver.find_element_by_xpath(f'//{Xpath.CAPTCHA_FRAME}')
                    self.driver.switch_to.frame(captcha)
                    captcha_task_description = self.driver.find_element_by_xpath(f'//{Xpath.CAPTCHA_TASK_DESCRIPTION}').text
                    captcha_task_grid = self.driver.find_element_by_xpath(f'//{Xpath.CAPTCHA_TASK_GRID}')
                    captcha_task_grid_location = self.get_absolute_position_of_element(
                        captcha_location, captcha_task_grid.location, captcha_task_grid.size)
                    captcha_screenshot_base64 = self.screenshot_screen_area(*captcha_task_grid_location)
                    captcha_solver = CaptchaSolver(captcha_screenshot_base64, captcha_task_description)
                    images_to_click = captcha_solver.solve_captcha()
                    for image_number in images_to_click:
                        self.press_button(f'//{Xpath.CAPTCHA_TASK_IMAGE}[{image_number}]')
                    self.press_button(f'//{Xpath.BUTTON_CAPTCHA_VERIFY}')
                    sleep(5)
                    self.driver.switch_to.default_content()
                except selenium_exceptions.NoSuchElementException:
                    retries += 1
                    if retries >= RETRY_NUMBER_PER_PAGE:
                        raise UnableToBypassCaptcha
                    self.driver.refresh()
        except selenium_exceptions.NoSuchElementException:
            return

    def get_absolute_position_of_element(self, outer_frame: Dict,
                                         position_in_frame: Dict,
                                         element_size: Dict) -> Tuple[int, int, int, int]:
        """ Calculate absolute position of element in dynamically loaded frame """
        left = outer_frame['x'] + position_in_frame['x']
        top = outer_frame['y'] + position_in_frame['y']
        bottom = top + element_size['height']
        right = left + element_size['width']
        return top, left, bottom, right

    def screenshot_screen_area(self, top, left, bottom, right) -> str:
        """ Get screenshot of a page and crop to element """
        screenshot = self.driver.get_screenshot_as_png()
        image = Image.open(BytesIO(screenshot))
        cropped_image = image.crop((left, top, right, bottom))
        cropped_image_rgb = cropped_image.convert('RGB')
        buffered = BytesIO()
        cropped_image_rgb.save(buffered, format="JPEG")
        base64_image = base64.b64encode(buffered.getvalue())
        return base64_image

    def press_button(self, button_xpath: str = None, button_object: Selector = None) -> None:
        """ Find and press button with given xpath or given button object"""
        if button_xpath:
            retries = 0
            while True:
                sleep(1)
                try:
                    button = self.driver.find_element_by_xpath(button_xpath)
                    self.driver.execute_script("arguments[0].click();", button)
                    sleep(1)
                    break
                except selenium_exceptions.NoSuchElementException as e:
                    retries += 1
                    if retries >= RETRY_NUMBER_PER_PAGE:
                        raise e
        elif button_object:
            self.driver.execute_script("arguments[0].click();", button_object)
        else:
            raise AttributeError('Either button_xpath or button_object mut be passed to press_button function.')


class LastPage(Exception):
    pass


class UnableToBypassCaptcha(Exception):
    pass
