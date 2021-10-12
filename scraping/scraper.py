import datetime
import sys
import argparse
from scrapyscript import Job, Processor
from scraping.spiders import QuestionSpider


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('url', help='First page of the questions you want to scrap')
    parser.add_argument('--page_limit', help='Limit of pages to scrap')
    args = parser.parse_args()

    scraping_job = Job(QuestionSpider, start_urls=[args.url], page_limit=args.page_limit)

    processor = Processor(settings={
        'FEED_URI': 'questions_' + datetime.datetime.today().strftime('%y%m%d') + '.json',
        'FEED_FORMAT': 'json',
        'FEED_EXPORTERS': {
            'json': 'scrapy.exporters.JsonItemExporter',
        },
        'FEED_EXPORT_ENCODING': 'utf-8',
    })

    data = processor.run([scraping_job])
