class Xpath:
    """ Xpath constants for use in scrapy spider """
    BUTTON_REVEAL_SOLUTION = "div[contains(@class, 'card-body')]/a[contains(@class, 'reveal-solution')]"
    BUTTON_NEXT_PAGE = "a[contains(@class, 'btn-success') and contains(text(), 'Next Questions')]"
    BUTTON_NOT_A_ROBOT = "button[contains(@class, 'g-recaptcha')]"
    BUTTON_LAST_PAGE_DISCLAIMER = """button[contains(text(), "Close and don't show again")]"""
    BUTTON_CAPTCHA_VERIFY = "div[contains(@title, 'Submit Answers') or contains(@title, 'Next Challenge') " \
                            "or contains(@title, 'Skip Challenge')]"
    CAPTCHA_FRAME = "iframe[contains(@title, 'Main content of the hCaptcha challenge')]"
    CAPTCHA_CONTAINER = CAPTCHA_FRAME + '/../..'
    CAPTCHA_TASK_GRID = "div[@class='task-grid']"
    CAPTCHA_TASK_DESCRIPTION = "div[@class='prompt-text']"
    CAPTCHA_TASK_IMAGE = "div[@class='task-grid']/div[@class='task-image']"
    QUESTION_LIST = "div[@class='questions-container']/div[contains(@class, 'exam-question-card')]"
    QUESTION_HEADER = "div[contains(@class, 'card-header')]"
    QUESTION_BODY = "div[contains(@class, 'card-body')]"
    QUESTION_ANSWER = "p[contains(@class, 'question-answer')]"
    QUESTION_TITLE = QUESTION_HEADER + "/text()"
    QUESTION_TOPIC = QUESTION_HEADER + "/span[contains(@class, 'question-title-topic')]/text()"
    QUESTION_TEXT = QUESTION_BODY + "/p[contains(@class, 'card-text')]/text()"
    QUESTION_ANSWER_VARIANTS = QUESTION_BODY + "/div[contains(@class, 'question-choices-container')]/ul/li"
    QUESTION_NUMBER_OF_COMMENTS = QUESTION_BODY + "/a[contains(@class, 'question-discussion-button')]" \
                                                  "/span[contains(@class, 'badge')]/text()"
    QUESTION_CORRECT_ANSWER_LETTER = QUESTION_ANSWER + "/span[@class='correct-answer-box']" \
                                                       "/span[@class='correct-answer']/text()"
    QUESTION_CORRECT_ANSWER_COMMENT = QUESTION_ANSWER + "/span[@class='answer-description']/descendant::text()"
    QUESTION_VARIANT_LETTER = "span/text()"
    QUESTION_VARIANT_TEXT = "span/following-sibling::text()"