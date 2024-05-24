import scrapy
from scrapy.linkextractors.lxmlhtml import LxmlLinkExtractor
from urllib.parse import urlparse
import queue
from ..items import ProjectItem

class UrlsSpider(scrapy.Spider):
    name = 'scraping'
    start_urls = [
        #  'https://www.scrapingcourse.com/ecommerce/'
        #   'https://pdr-1111.com/'
        'https://newtoki338.com/'
    ]
    visited_urls = set()  # 방문한 URL을 추적하기 위한 집합
    visited_urls.update(
        [
            "www.naver.com",
            "www.google.com",
            "www.facebook.com",
            "www.twitter.com",
            "www.daum.net",
            "github.com",
            "wikipedia.org",
        ]
    )
    queue = queue.Queue()

    # keywords = set()
    # keywords.update(
    #     [
    #         "카지노",
    #         "슬롯게임",
    #         "배팅",
    #         "입금신청",
    #         "복권",
    #         "CASINO",
    #         "SLOT",
    #         "POKER",
    #     ]
    # )

    def parse(self, response):
        items = ProjectItem()
        # 현재 URL을 방문한 URL 집합에 추가
        for link in LxmlLinkExtractor(unique=True).extract_links(response):
            current_url = urlparse(link.url).netloc

            if current_url not in self.visited_urls:
                self.visited_urls.add(current_url)
                self.queue.put(link.url)

                print(current_url)
                items['url'] = current_url
                yield items
            #print("현재큐:", list(self.queue.queue))

        yield from self.process_queue()

    def process_queue(self):
        while not self.queue.empty():
            next_url = self.queue.get()

            yield scrapy.Request(next_url, callback=self.parse, errback=self.error_handler)


# 오류 제어 핸들러
    def error_handler(self, failure):
        if failure.check(scrapy.exceptions.IgnoreRequest):
            print("Ignoring error:", failure.getErrorMessage())
        else:
            print("Error occurred:", failure.getErrorMessage())

        # 기존 큐에서 다음 URL을 가져옴
        if not self.queue.empty():
            next_url = self.queue.get()
            yield scrapy.Request(next_url, callback=self.parse, errback=self.error_handler)
