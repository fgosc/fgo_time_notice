import io
import json

import boto3
from chalice import Chalice, Cron

from chalicelib.scraper import make_notices
from chalicelib import settings

app = Chalice(app_name='fgo_time_notice')
s3resource = boto3.resource('s3')
s3bucket = s3resource.Bucket(settings.BUCKET_NAME)


def run():
    notices = make_notices()
    data = json.dumps(notices, ensure_ascii=False)
    bio = io.BytesIO(data.encode('utf-8'))

    obj = s3bucket.Object(settings.JSON_PATH)
    obj.upload_fileobj(bio, ExtraArgs={'ContentType': 'application/json'})


@app.route('/run')
def runapi():
    try:
        _run()
        return {'result': 'ok'}
    except Exception as e:
        app.log.error(e)
        return {'result': 'error'}


# 設定は UTC 時刻基準 (AWS の仕様)
# 1800-2200 の間で毎時10分、40分
@app.schedule(Cron('10,40', '9-13', '*', '*', '?', '*'))
def run(event):
    _run()
