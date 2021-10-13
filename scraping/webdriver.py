import base64
from io import BytesIO
from time import sleep
from typing import Tuple, Dict

from scrapy import Selector
from scrapy.http.response.html import HtmlResponse
from selenium import webdriver
import selenium.common.exceptions as selenium_exceptions
from PIL import Image

from constants import RETRY_NUMBER_PER_PAGE
from scraping.xpath import Xpath
from scraping.captcha_solver import CaptchaSolver


class WebDriver:
    def __init__(self, url):
        """ Initialize webdriver """
        options = webdriver.FirefoxOptions()
        options.headless = True
        self.driver = webdriver.Firefox(options=options)
        self.driver.get(url)

    def __del__(self):
        """ Close webdriver """
        self.driver.close()

    def close_last_page_disclaimer(self) -> None:
        """ Close disclaimer window on the last page """
        xpath = f'//{Xpath.BUTTON_LAST_PAGE_DISCLAIMER}'
        try:
            button = self.driver.find_element_by_xpath(xpath)
            self.press_button(button)
        except selenium_exceptions.NoSuchElementException:
            pass

    def solve_captcha(self, response: HtmlResponse) -> None:
        """ Solve captcha """
        retries = 0
        try:
            while captcha := self.driver.find_element_by_xpath(f'//{Xpath.CAPTCHA_FRAME}'):
                try:
                    self.driver.switch_to.frame(captcha)
                    try:
                        captcha_task_description = self.driver.find_element_by_xpath(
                            f'//{Xpath.CAPTCHA_TASK_DESCRIPTION}').text
                    except selenium_exceptions.NoSuchElementException:
                        screen = self.driver.get_screenshot_as_base64()
                        raise selenium_exceptions.NoSuchElementException
                    captcha_task_grid = self.driver.find_element_by_xpath(f'//{Xpath.CAPTCHA_TASK_GRID}')
                    captcha_screenshot_base64 = captcha_task_grid.screenshot_as_base64
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

    def screenshot_screen_area(self, top, left, bottom, right) -> bytes:
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

    def get_current_source(self):
        return self.driver.page_source


class UnableToBypassCaptcha(Exception):
    pass
