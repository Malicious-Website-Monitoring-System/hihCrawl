import scrapy
import re
from collections import Counter

class GetSpider(scrapy.Spider):
    name = "get"
    allowed_domains = ["pdr-1111.com"]
    start_urls = ["https://pdr-1111.com/"]

    getTexts = []

    def parse(self, response):
        for text in response.xpath('//text()').extract():
            before_text = text.strip()
            before_text = self.clean_text(before_text)
            self.getTexts.append(before_text)
        cleaned_texts = [text for text in self.getTexts if text] #빈 문자열이 아닌 것만 뽑기

        print(cleaned_texts)

        word_count = Counter(cleaned_texts)
        for word, count in word_count.items():
            print(f"'{word}': {count}번")


    def clean_text(self, text):
        # Remove alphabet characters and special characters
        cleaned_text = re.sub('[a-zA-Z0-9]', '', text)
        cleaned_text = re.sub('[\{\}\[\]\/?.,;:|\)*~`!^\-_+<>@\#$%&\\\=\(\'\"]', '', cleaned_text)
        # Remove any remaining whitespace, tabs, and newlines
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        return cleaned_text
