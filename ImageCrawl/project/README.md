#0529

ImageCrawl 폴더 참고는 spiders/image.py, items.py

사용 전 Tesseract-ocr 설치 필요
https://github.com/UB-Mannheim/tesseract/wiki 해당 링크 들어가 맞는 버전 설치



#0530

주석 # 3)번까지 참고 부탁드립니다....


#0607, image_modify 참고

수정
1(50번째 줄). image 불러오는 속성은 src와 data-original(추가)
src 속성은 이미지를 즉시 로드하여 표시하는 데 사용되고, data-original 속성은 이미지를 나중에 필요할 때 로드하는 데 사용


2(71번째 줄). gif 파일 추출 시 첫 프레임만 추출되는 경향이 있음
마지막 프레임에 모든 내용이 집중되는 경향이 있으므로 차라리 마지막 프레임만 추출시키도록 수정
