import io
import json

import boto3
from chalice import Chalice, Cron

from chalicelib.scraper import get_pages
from chalicelib import settings

app = Chalice(app_name='fgo_time_notice')
s3resource = boto3.resource('s3')
s3bucket = s3resource.Bucket(settings.BUCKET_NAME)


# 設定は UTC 時刻基準 (AWS の仕様)
# 1800-2200 の間で毎時10分、40分
@app.schedule(Cron('10,40', '9-13', '*', '*', '?', '*'))
def run(event):
    news_url = "https://news.fate-go.jp"
    maintenance_url = "https://news.fate-go.jp/maintenance"
    notices_n = get_pages(news_url)
    notices_m = get_pages(maintenance_url)
    data = json.dumps(notices_n + notices_m, ensure_ascii=False)
    bio = io.BytesIO(data.encode('utf-8'))

    obj = s3bucket.Object(settings.JSON_PATH)
    obj.upload_fileobj(bio, ExtraArgs={'ContentType': 'application/json'})
