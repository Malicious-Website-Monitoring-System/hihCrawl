import cv2
import numpy as np
import pytesseract
import re
import scrapy
from io import BytesIO
from PIL import Image
from scrapy.http import Request
from urllib.parse import urljoin
from ..items import ProjectItem

#pytesseract 사용 전 https://github.com/UB-Mannheim/tesseract/wiki 설치!!!!
#테서랙트 경로
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


class ImageSpider(scrapy.Spider):
    name = "image"
    #예시링크
    start_urls = [
        "https://newtoki338.com/"
    ]

    #도메인 가져오기
    def parse(self, response):
        #parse에서 넘길 때는 yield from 사용!!!!!
        #그냥 self.extract_in_image(response) 이거 쓰면 안되더라고요....?
        yield from self.extract_in_image(response)

    def extract_in_image(self, response):
        # 도메인의 이미지 가져오기
        img_urls = response.css('img::attr(src)').extract()

        # 이미지 불러오고 변수에 저장하기
        for img_url in img_urls:
            if not img_url.startswith(('http', 'https')):
                img_url = urljoin(response.url, img_url)
            yield Request(img_url, callback=self.parse_image, errback=self.errback_image)

    def parse_image(self, response):

        try:
            #opencv랑 PIL중에 머가 좋지
            img = Image.open(BytesIO(response.body))

            # 너무 작은 아이콘은 거르기
            min_image_width = 50  # 최소 이미지 너비
            min_image_height = 50  # 최소 이미지 높이
            width, height = img.size

            #넘어간 item은 pipelines에서 사용
            if width > min_image_width and height > min_image_height:
                #이미지 전처리 함수 사용여부
                #img = self.clean_image(img)

                text = pytesseract.image_to_string(img, lang='kor')
                gettext = self.process_text(text)
                item = ProjectItem()
                item['text'] = gettext
                yield item

            yield None

        except IOError as e:
            yield None

    def errback_image(self, failure):
        yield None

    #적절한 노이즈 제거 방법을 찾기!!!!!!!!!!!!!!
    def clean_image(self, image):
        #opencv사용을 위해 쓰기
        img_cv2 = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

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
