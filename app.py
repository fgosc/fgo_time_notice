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


# The view function above will return {"hello": "world"}
# whenever you make an HTTP GET request to '/'.
#
# Here are a few more examples:
#
# @app.route('/hello/{name}')
# def hello_name(name):
#    # '/hello/james' -> {"hello": "james"}
#    return {'hello': name}
#
# @app.route('/users', methods=['POST'])
# def create_user():
#     # This is the JSON body the user sent in their POST request.
#     user_as_json = app.current_request.json_body
#     # We'll echo the json body back to the user in a 'user' key.
#     return {'user': user_as_json}
#
# See the README documentation for more examples.
#
