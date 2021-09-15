import scrapy
from scrapy.http.response.html import HtmlResponse
from selenium import webdriver
import selenium.common.exceptions as selenium_exceptions

from scraping.xpath import Xpath


class QuestionSpider(scrapy.Spider):
    name = 'questions'
    start_urls = ['https://www.examtopics.com/exams/amazon/aws-certified-solutions-architect-associate-saa-c02/view/']

    def __init__(self):
        """ Initialize webdriver """
        self.driver = webdriver.Firefox()
        super().__init__()

    def __del__(self):
        """ Close webdriver """
        self.driver.close()

    def parse(self, response: HtmlResponse) -> None:
        """ Parse URL """
        self.driver.get(response.request.url)
        self.solve_captcha(response)
        self.close_last_page_disclaimer()
        while True:
            for number_on_page, question in enumerate(response.xpath('//' + Xpath.QUESTION_LIST)):
                self.press_reveal_solution(number_on_page)
                parsed_question = self.parse_question(question)
                yield parsed_question
            try:
                next_page_relative_url = self.get_next_page(response)
                next_page_full_url = response.urljoin(next_page_relative_url)
                yield scrapy.Request(next_page_full_url, callback=self.parse)
            except LastPage:
                break

    def parse_question(self, question_selector: scrapy.Selector) -> dict:
        """ Parse single question """
        question_title = question_selector.xpath('.//' + Xpath.QUESTION_TITLE).get().strip()
        question_topic = question_selector.xpath('.//' + Xpath.QUESTION_TOPIC).get().strip()
        question_text = question_selector.xpath(".//" + Xpath.QUESTION_TEXT).get().strip()
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
        self.press_button(xpath)

    def get_next_page(self, response: HtmlResponse) -> str:
        next_page_button = response.xpath('//' + Xpath.BUTTON_NEXT_PAGE)
        if not next_page_button:
            raise LastPage
        else:
            return next_page_button.attrib['href']

    def solve_captcha(self, response: HtmlResponse) -> None:
        """ Stub for captcha resolve """
        not_a_robot_xpath = f'//{Xpath.BUTTON_NOT_A_ROBOT}'
        self.press_button(not_a_robot_xpath)
        captcha_xpath = f'//{Xpath.CAPTCHA}'
        captcha_frame = response.xpath(captcha_xpath)
        # Implement captcha resolve here
        pass

    def press_button(self, button_xpath: str) -> None:
        """ Find and press button with given xpath """
        try:
            button = self.driver.find_element_by_xpath(button_xpath)
            self.driver.execute_script("arguments[0].click();", button)
        except selenium_exceptions.NoSuchElementException:
            # Suppress for now
            pass





class LastPage(Exception):
    pass
