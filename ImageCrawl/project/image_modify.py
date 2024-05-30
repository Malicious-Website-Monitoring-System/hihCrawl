import pytesseract
import re
import scrapy
from io import BytesIO
from PIL import Image, UnidentifiedImageError
from scrapy.http import Request
from urllib.parse import urljoin
from collections import deque, Counter

#pytesseract 사용 전 https://github.com/UB-Mannheim/tesseract/wiki 설치!!!!
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


class ImageSpider(scrapy.Spider):
    name = "image"

    def __init__(self, *args, **kwargs):
        super(ImageSpider, self).__init__(*args, **kwargs)
        self.divide_file = open('divide.txt', 'w') 
        self.image_file = open('image.txt', 'w')
        self.hosts_queue = deque(open('D:/hosts.txt', 'r', encoding='utf-8').read().strip().split("\n"))
        self.logger.info(f"Loaded {len(self.hosts_queue)} URLs from hosts.txt")


    def start_requests(self):
        if self.hosts_queue:
            current_url = self.hosts_queue.popleft()
            yield scrapy.Request(url=current_url, callback=self.parse, errback=self.errback)


    def parse(self, response):
        current_url = response.url
        texts = []

# 1) 이부분 참고 부탁드려요!!
        image_texts = self.extract_in_image(response, current_url)
        yield from (text for text in image_texts)
        if image_texts:
            texts.extend(image_texts)
# 여기까지

        count_words = self.extract_words_count(texts)
        self.save_words_count(current_url, count_words) 

        if self.hosts_queue:
            next_url = self.hosts_queue.popleft()
            yield scrapy.Request(url=next_url, callback=self.parse, errback=self.errback)

    def extract_in_image(self, response, current_url):
        self.image_file.write(f"{current_url}\n")  
        img_urls = response.css('img::attr(src)').extract()
        for img_url in img_urls:
            if not img_url.startswith(('http', 'https')):
                img_url = urljoin(response.url, img_url)
            self.logger.info(f"Queuing image for download: {img_url}")
            yield Request(img_url, callback=self.parse_image, meta={'img_url': img_url, 'current_url': current_url})

    def parse_image(self, response):
        img_url = response.meta['img_url']
        current_url = response.meta['current_url']
        self.logger.info(f"Processing image: {img_url}")

        try:
            img = Image.open(BytesIO(response.body))

            if img.format not in ['JPEG', 'PNG', 'GIF']:
                self.logger.error(f"Unsupported image format: {img.format}")
                return

            min_image_width = 50  
            min_image_height = 50  
            width, height = img.size
            self.logger.info(f"Image size: {width}x{height}")

# 2) kor+eng로 수정
            if width > min_image_width and height > min_image_height:
                text = pytesseract.image_to_string(img, lang='kor+eng')
                gettext = self.process_text(text)
                self.logger.info(f"Extracted text: {gettext}")

                if gettext:
                    self.image_file.write(f"{img_url} : {', '.join(gettext)}\n")
                    return gettext
        except UnidentifiedImageError as e:
            self.logger.error(f"An error occurred while processing the image: cannot identify image file {e}")
        except IOError as e:
            self.logger.error(f"An error occurred while processing the image: {e}")

    def process_text(self, text):
        text = re.sub(r'\b[ㄱ-ㅎㅏ-ㅣ]\b', '', text)
        # 3) 여기 re.sub('[a-zA-Z0-9]', '', text) 이렇게 되어 있을텐데 [0-9] 이걸로 수정 부탁드립니다.
        text = re.sub('[0-9]', '', text)
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\d+', '', text)
        text = re.sub(r'\s+', ' ', text)
        word_list = text.strip().split()
        cleaned_word_list = [re.sub(r'[ㄱ-ㅎㅏ-ㅣ]', '', word) for word in word_list]
        filtered = [word for word in cleaned_word_list if len(word) > 1]
        return filtered

    def extract_words_count(self, words):
        return dict(Counter(words))

    def save_words_count(self, url, count_words):
        self.logger.info(f"Saving word counts for URL: {url}")
        for word, count in count_words.items():
            self.divide_file.write(f"{url} ---> {word}: {count}\n")

    def errback(self, failure):
        self.logger.error(repr(failure))
        if self.hosts_queue:
            next_url = self.hosts_queue.popleft()
            self.logger.info(f"Queueing next URL after error: {next_url}")
            yield scrapy.Request(url=next_url, callback=self.parse, errback=self.errback)

    def closed(self, reason):
        self.divide_file.close()
