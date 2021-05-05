import scrapy
from scrapy import cmdline
from scrapy.crawler import CrawlerProcess
from multiprocessing.context import Process

from .opinions_spider import OpinionsSpider


class UrlsSpider(scrapy.Spider):
    name = 'urls'
    start_urls = ['https://www.debate.org/opinions/?sort=popular']
    base_url = 'https://www.debate.org'

    # opinions = OpinionsSpider()
    popular_opinions = []

    result = None

    def parse(self, response):
        # yield {"page": response.url}
        for x in range(5):
            url = response.css("a.a-image-contain")[x].attrib['href']
            topic = response.css("span.q-title")[x].css("::text").get()
            self.popular_opinions.append(self.base_url + url)
        yield {'urls': self.popular_opinions}
        #

    # process = CrawlerProcess()
    # process.crawl(OpinionsSpider, url_list=popular_opinions)
    # process.start(stop_after_crawl=False)
