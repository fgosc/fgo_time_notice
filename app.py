import io
import json

import boto3
from chalice import Chalice, Rate

from chalicelib.scraper import get_pages
from chalicelib import settings

app = Chalice(app_name='fgo_time_notice')
s3resource = boto3.resource('s3')
s3bucket = s3resource.Bucket(settings.BUCKET_NAME)


@app.schedule(Rate(12, unit=Rate.HOURS))
def run(event, context):
    news_url = "https://news.fate-go.jp"
    notice = get_pages(news_url)
    data = json.dumps(notice, ensure_ascii=False)
    bio = io.BytesIO(data.encode('utf-8'))

    obj = s3bucket.Object(settings.JSON_PATH)
    obj.upload_fileobj(bio, ExtraArgs={'ContentType': 'application/json'})
