import openai
import logging
from classify.models import WordCount, FullSentence, Hosts, Normal, Casino, Adult, Copyright
from konlpy.tag import Okt
from collections import Counter
from asgiref.sync import sync_to_async
import jpype
import os

# 로깅 설정
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# OPENAI_API_KEY 설정
OPENAI_API_KEY = ""
openai.api_key = OPENAI_API_KEY

# 형태소 분석기 객체 생성
okt = Okt()
if not jpype.isJVMStarted():
    jvmpath = os.path.join(os.environ['JAVA_HOME'], 'lib/jli/libjli.dylib')
    jpype.startJVM(jvmpath, "-Djava.class.path={}".format(os.environ['JAVA_HOME']), convertStrings=True)


# 미리 정의된 키워드를 가져오는 함수
async def get_predefined_keywords():
    logger.debug("Fetching predefined keywords from database")
    predefined_keywords = {
        "도박사이트": await sync_to_async(list)(Casino.objects.values_list('word', flat=True)),
        "성인사이트": await sync_to_async(list)(Adult.objects.values_list('word', flat=True)),
        "불법저작물배포사이트": await sync_to_async(list)(Copyright.objects.values_list('word', flat=True)),
        "정상": await sync_to_async(list)(Normal.objects.values_list('word', flat=True)),
    }
    return predefined_keywords

# GPT 문자 길이가 너무 길 경우 대비
def tokenize_text(text):
    tokens = text.split()  # 공백을 기준으로 텍스트를 나누어 리스트로 만듦
    return tokens

def truncate_text_by_token_limit(text, max_tokens=12000):
    tokens = tokenize_text(text)
    if len(tokens) <= max_tokens:
        return text  # 토큰 개수가 제한 이내이면 원본 텍스트 반환

    truncated_tokens = tokens[:max_tokens]  # 토큰 개수가 제한을 초과할 경우 일부 토큰만 남기기
    truncated_text = ' '.join(truncated_tokens)  # 잘린 토큰을 다시 문자열로 합치기
    return truncated_text

# 숫자로 응답받기 위한 함수
async def classify_with_keywords(qa):
    question = truncate_text_by_token_limit(qa)
    try:
        response = await sync_to_async(openai.ChatCompletion.create)(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": question}
            ]
        )
        # 문자열로 출력될 경우 코드 대비
        classification = response.choices[0].message['content'].strip()
        if not classification.isdigit():
            numbers = [int(num) for num in classification if num.isdigit()]
            classification = int(''.join(map(str, numbers)))

        logger.debug(f"Received classification: {classification}")
        return classification

    except openai.error.APIError as e:
        logger.error(f"OpenAI API error: {e}")
        return "-1"

# 모든 키워드를 가져오는 함수
async def get_all_keywords(host):
    logger.debug(f"Fetching all keywords for host: {host}")
    words = await sync_to_async(list)(WordCount.objects
                                      .filter(host=host)
                                      .values_list('words', flat=True))
    return words

# 모든 키워드를 사용하여 사이트 분류
async def classify_all_keywords(host):
    logger.debug(f"Classifying site using all keywords for host: {host}")
    all_keywords = await get_all_keywords(host)
    if not all_keywords:
        logger.warning("No keywords found, returning '접속 불가 또는 존재하지않음'")
        return -1

    predefined_keywords = await get_predefined_keywords()
    predefined_keywords_sentence = {
        category: ", ".join(keywords)
        for category, keywords in predefined_keywords.items()
    }
    keywords_sentence = ", ".join(all_keywords)
    question = (f"웹사이트의 모든 키워드입니다: {keywords_sentence}. "
                f"미리 정의된 카테고리별 키워드는 다음과 같습니다. "
                f"도박사이트: {predefined_keywords_sentence['도박사이트']}, "
                f"성인사이트: {predefined_keywords_sentence['성인사이트']}, "
                f"불법저작물배포사이트: {predefined_keywords_sentence['불법저작물배포사이트']}, "
                f"정상: {predefined_keywords_sentence['정상']}. "
                "위 미리 정의된 카테고리별 키워드를 참고하여 웹사이트가 다음 중 어떤 종류인지 숫자로 판단해줘: "
                "도박사이트(0), 성인사이트(1), 불법저작물배포사이트(2), 정상(3). "
                "부연설명은 필요없어. 도박사이트면 그냥 '0' 이런식으로만 출력해주면 돼")

    return await classify_with_keywords(question)

# FullSentence 테이블에서 문장을 요약하는 함수
async def summarize_full_sentence(host):
    logger.debug(f"Summarizing full sentences for host: {host}")
    full_sentences = await sync_to_async(list)(
        FullSentence.objects.filter(host=host).values_list('full_sentence', flat=True))

    combined_sentences = " ".join(full_sentences)
    question = f"다음 문장을 3~4문장으로 요약해줘: {combined_sentences}"

    # OpenAI API 호출 시 예외 처리 추가
    try:
        response = await sync_to_async(openai.ChatCompletion.create)(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": question}
            ]
        )
        summary = response.choices[0].message['content'].strip()
        logger.debug(f"Received summary: {summary}")
        return summary
    except openai.error.APIError as e:
        logger.error(f"OpenAI API error: {e}")
        return "알 수 없음"


# 요약문을 사용하여 사이트 분류
async def classify_summary(host):
    logger.debug(f"Classifying site using summary for host: {host}")
    summary = await summarize_full_sentence(host)
    predefined_keywords = await get_predefined_keywords()
    predefined_keywords_sentence = {
        category: ", ".join(keywords)
        for category, keywords in predefined_keywords.items()
    }
    question = (f"다음 요약문을 기반으로 웹사이트가 어떤 종류인지 숫자로 판단해줘: {summary}. "
                f"미리 정의된 카테고리별 키워드는 다음과 같습니다. "
                f"도박사이트: {predefined_keywords_sentence['도박사이트']}, "
                f"성인사이트: {predefined_keywords_sentence['성인사이트']}, "
                f"불법저작물배포사이트: {predefined_keywords_sentence['불법저작물배포사이트']}, "
                f"정상: {predefined_keywords_sentence['정상']}. "
                "위 미리 정의된 카테고리별 키워드를 참고하여 웹사이트가 다음 중 어떤 종류인지 숫자로 판단해줘"
                "위 카테고리별들로 많이 나온 단어들을 추출해온건데, 이 요약문이 어느위치에 포함되어있는지 확인해주면 돼."
                "특히 정상사이트랑 불법저작물배포사이트 는 구별하기 힘드니까 잘 판단해서"
                "어떤 종류인지 숫자로 판단해주면돼"
                "도박사이트(0), 성인사이트(1), 불법저작물배포사이트(2), 정상(3). "
                "부연설명은 필요없어. 도박사이트면 그냥 '0' 이런식으로만 출력해주면 돼"
                )

    return await classify_with_keywords(question)

# 유사도를 확인하는 함수
async def check_similarity_with_predefined(host):
    logger.debug(f"Checking similarity for host: {host}")
    all_keywords = await get_all_keywords(host)
    predefined_keywords = await get_predefined_keywords()

    # 유사도 계산
    similarity_scores = {}
    for category, keywords in predefined_keywords.items():
        if not keywords:
            similarity_scores[category] = -1  # 키워드가 없으면 유사도 점수는 -1
            continue

        common_words = set(all_keywords) & set(keywords)
        similarity_scores[category] = len(common_words)

    logger.debug(f"Similarity scores: {similarity_scores}")
    max_similarity_score = max(similarity_scores.values())

    if max_similarity_score == -1 or max_similarity_score == 0:
        return [-1]

    most_similar_categories = [category for category, score in similarity_scores.items() if score == max_similarity_score]
    logger.debug(f"Most similar categories: {most_similar_categories}")

    # 카테고리를 숫자로 변환하여 리스트로 반환
    similarity_classification_map = {
        "도박사이트": 0,
        "성인사이트": 1,
        "불법저작물배포사이트": 2,
        "정상": 3,
        -1: -1,
    }

    return [similarity_classification_map.get(category) for category in most_similar_categories]


# 최종 분류를 결정하는 함수
async def final_classification(host):
    logger.debug(f"Starting final classification for host: {host}")
    classifications = []


    # 모든 단어 기반 분류
    all_keywords_classification = await classify_all_keywords(host)
    classifications.append(all_keywords_classification)
    logger.debug(f"All keywords classification: {all_keywords_classification}")

    # 요약문 기반 분류
    summary_classification = await classify_summary(host)
    classifications.append(summary_classification)
    logger.debug(f"Summary classification: {summary_classification}")

    # 유사도 기반 분류
    similarity_classification = await check_similarity_with_predefined(host)
    logger.debug(f"Similarity classification: {similarity_classification}")
    classifications.extend(similarity_classification)


    # 유사도 분류 결과를 제외한 다른 분류 결과는 이미 숫자 형태이므로 그대로 사용
    filtered_classifications = []
    for c in classifications:
        if c not in [-1, '-1']:
            try:
                filtered_classifications.append(int(float(c)))
            except ValueError:
                # 숫자로 변환할 수 없는 값은 무시하거나 로그를 남깁니다.
                print(f"Invalid value for classification: {c}")

    if not filtered_classifications:
        final_classification_number = -1

    else:
        final_classification_number = Counter(filtered_classifications).most_common(1)[0][0]


    # if -1 in classifications:
    #     final_classification_number = -1

    classification_map = {
        0: "도박사이트",
        1: "성인사이트",
        2: "불법저작물배포사이트",
        3: "정상",
        -1: "알 수 없음"
    }

    final_classification = classification_map.get(final_classification_number, "알 수 없음")
    logger.debug(f"Final classification result: {final_classification}")
    return final_classification
