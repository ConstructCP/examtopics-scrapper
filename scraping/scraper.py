import datetime
from scrapyscript import Job, Processor
from scraping.spiders import QuestionSpider


if __name__ == '__main__':
    githubJob = Job(QuestionSpider)

    processor = Processor(settings={
        'FEED_URI': 'questions_' + datetime.datetime.today().strftime('%y%m%d') + '.json',
        'FEED_FORMAT': 'json',
        'FEED_EXPORTERS': {
            'json': 'scrapy.exporters.JsonItemExporter',
        },
        'FEED_EXPORT_ENCODING': 'utf-8',
    })

    data = processor.run([githubJob])
