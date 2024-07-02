#urlcrawl/app.py

from django.apps import AppConfig
from django.conf import settings

class UrlcrawlConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'urlcrawl'

    # 자동화 사용 시 주석 해제
    # def ready(self):
    #     if settings.SCHEDULER_DEFAULT:
    #         from . import task
    #         task.start()