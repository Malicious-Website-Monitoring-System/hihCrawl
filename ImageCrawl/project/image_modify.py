import pytesseract
import re
import scrapy
from io import BytesIO
from PIL import Image, UnidentifiedImageError
from scrapy.http import Request
from urllib.parse import urljoin
from collections import deque, Counter

#pytesseract 사용 전 https://github.com/UB-Mannheim/tesseract/wiki 설치!!!!
#테서랙트 경로
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


class ImageSpider(scrapy.Spider):
    name = "image"

    def __init__(self, *args, **kwargs):
        super(ImageSpider, self).__init__(*args, **kwargs)
        self.divide_file = open('divide.txt', 'w')  # 텍스트 단어를 기록할 파일 열기
        self.image_file = open('image.txt', 'w')  # 이미지 단어를 기록할 파일 열기
        self.hosts_queue = deque(open('D:/hosts.txt', 'r', encoding='utf-8').read().strip().split("\n"))
        self.logger.info(f"Loaded {len(self.hosts_queue)} URLs from hosts.txt")


    def start_requests(self):
        if self.hosts_queue:
            current_url = self.hosts_queue.popleft()
            yield scrapy.Request(url=current_url, callback=self.parse, errback=self.errback)


    def parse(self, response):
        current_url = response.url

        # 이미지 텍스트 추출 및 파일 기록
        texts = []

# 이부분 참고 부탁드려요!!
        image_texts = self.extract_in_image(response, current_url)
        yield from (text for text in image_texts)
        if image_texts:
            texts.extend(image_texts)
# 여기까지

        count_words = self.extract_words_count(texts)  # 단어 개수 세기
        self.save_words_count(current_url, count_words)  # 단어 개수 파일에 저장

        if self.hosts_queue:
            next_url = self.hosts_queue.popleft()
            yield scrapy.Request(url=next_url, callback=self.parse, errback=self.errback)

    # 이미지에서 단어 추출하는 코드
    def extract_in_image(self, response, current_url):
        self.image_file.write(f"{current_url}\n")  # URL 기록
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

            # 이미지 형식 확인 추가
            if img.format not in ['JPEG', 'PNG', 'GIF']:
                self.logger.error(f"Unsupported image format: {img.format}")
                return

            min_image_width = 50  # 최소 이미지 너비
            min_image_height = 50  # 최소 이미지 높이
            width, height = img.size
            self.logger.info(f"Image size: {width}x{height}")

            if width > min_image_width and height > min_image_height:
                # tesseract사용
                text = pytesseract.image_to_string(img, lang='kor+eng')
                gettext = self.process_text(text)
                self.logger.info(f"Extracted text: {gettext}")

                # 이미지 URL과 텍스트 기록
                if gettext:
                    self.image_file.write(f"{img_url} : {', '.join(gettext)}\n")
                    return gettext
        except UnidentifiedImageError as e:
            self.logger.error(f"An error occurred while processing the image: cannot identify image file {e}")
        except IOError as e:
            self.logger.error(f"An error occurred while processing the image: {e}")

    def process_text(self, text):
        text = re.sub(r'\b[ㄱ-ㅎㅏ-ㅣ]\b', '', text)
        text = re.sub('[a-zA-Z0-9]', '', text)
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\d+', '', text)
        text = re.sub(r'\s+', ' ', text)
        word_list = text.strip().split()
        cleaned_word_list = [re.sub(r'[ㄱ-ㅎㅏ-ㅣ]', '', word) for word in word_list]
        filtered = [word for word in cleaned_word_list if len(word) > 1]
        return filtered

    # 단어 개수 추출하기
    def extract_words_count(self, words):
        return dict(Counter(words))

    # 단어 개수 추출한 거 파일에 저장하기
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
