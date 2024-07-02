#urlcrawl/task.py

import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from .views import one, two
from .views import start_crawl, classify_urls
import logging
from django.test import RequestFactory

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def start():
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), 'djangojobstore')

    def one_task():
        logger.info("Starting one")
        one()
        #urlcrawl 작업은 one() 삭제 후 밑의 주석 풀기
        #request = RequestFactory().post('/dummy-url-clean/')
        #start_crawl(request)

    async def two_task():
        logger.info("Starting two")
        request = RequestFactory().post('/dummy-url-clean/')
        await classify_urls(request)

    # 첫 번째 작업 추가, urlcrawl
    # 테스트를 위해 10초마다 실행되도록 설정
    # second 삭제 후 주석을 풀면 특정 시간마다 돌아간다.
    scheduler.add_job(
        one_task,
        'cron',
        second='*/10',
        # hour='4, 8, 12, 16, 20',
        # minute='0',
        # second='0',
        name='one_task',
        id='one_task'
    )

    # 두 번째 작업 추가, classify_urls
    # 테스트를 위해 1분마다 실행되도록 설정
    # minute 삭제 후 주석을 풀면 특정 시간마다 돌아간다.
    scheduler.add_job(
        lambda: asyncio.run(two_task()),
        'cron',
        minute='*/1',
        # hour='2, 6, 10, 14, 18, 22',
        # minute='0',
        # second='0',
        name='two_task',
        id='two_task'
    )

    scheduler.start()
    logger.info("Scheduler started")
