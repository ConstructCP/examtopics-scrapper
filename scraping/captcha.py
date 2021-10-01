from typing import Dict, List
import time
import requests
import re
import base64
from constants import RETRY_CAPTCHA_ATTEMPTS
from secrets import twocaptcha_api_key


class CaptchaSolver:
    post_url = 'http://2captcha.com/in.php'
    get_url = 'http://2captcha.com/res.php'

    def __init__(self, base64_image: base64, instructions: str):
        """ Initialize class with base64 encoded image and solving instructions """
        self.base64_image = base64_image
        self.instructions = instructions

    def prepare_send_image_request(self) -> Dict:
        """ Prepare request body for send image request """
        request_data = {
            'key': twocaptcha_api_key,
            'method': 'base64',
            'recaptcha': 1,
            'body': self.base64_image,
            'lang': 'en',
            'textinstructions': self.instructions,
            'recaptcharows': 3,
            'recaptchacols': 3,
            'can_no_answer': 1
        }
        return request_data

    def prepare_get_response_request(self, request_id: str) -> Dict:
        """ Prepare request body for get response request """
        request_data = {
            'key': twocaptcha_api_key,
            'action': 'get',
            'id': request_id
        }
        return request_data

    def send_image_for_recognition(self) -> str:
        """ Send image to 2captcha service for recognition. Return request id """
        request_data = self.prepare_send_image_request()
        response = requests.post(self.post_url, data=request_data)
        if 'OK' in response.text:
            request_id = response.text[3:]
            return request_id
        else:
            raise BadCaptchaRequest(response.text)

    def get_recognition_response(self, request_id: str) -> List[int]:
        """ Get result of image recognition. Return numbers of images to click """
        request_data = self.prepare_get_response_request(request_id)
        while True:
            time.sleep(5)
            recognition_status_request_data = {
                'key': twocaptcha_api_key,
                'action': 'get',
                'id': request_id
            }
            response = requests.get(self.get_url, params=request_data)
            if 'CAPCHA_NOT_READY' not in response.text:
                break
        answer = response.text
        if 'OK' in answer:
            numbers_offset = answer.find('click:') + len('click:')
            image_numbers_to_click = [int(num) for num in re.findall(r'\d+', answer[numbers_offset:])]
            return image_numbers_to_click
        else:
            raise BadCaptchaRequest(answer)

    def solve_captcha(self) -> List[int]:
        """ Solve captcha and return numbers of images to click """
        retries = 0
        while True:
            try:
                request_id = self.send_image_for_recognition()
                image_numbers_to_click = self.get_recognition_response(request_id)
                return image_numbers_to_click
            except BadCaptchaRequest as e:
                retries += 1
                if retries > RETRY_CAPTCHA_ATTEMPTS:
                    raise e


class BadCaptchaRequest(Exception):
    pass
