#!/usr/bin/env python3
import argparse
import logging
import datetime

import requests

logger = logging.getLogger(__name__)
event_url = "https://api.atlasacademy.io/export/JP/basic_event.json"

NO_DEADLINE_ENDEDAT = 1893423600


def make_data_from_api(web_notices, dtime=datetime.datetime.now()):
    # dtime: 指定時間(datetime)
    notices = []
    r_get = requests.get(event_url)
    event_list = r_get.json()
    for event in event_list:
        # open
        notice = {}
        stime = datetime.datetime.fromtimestamp(event["startedAt"])
        etime = datetime.datetime.fromtimestamp(event["endedAt"])
        td_s = dtime - stime
        td_e = etime - dtime
        if td_s.total_seconds() >= 0 and td_e.total_seconds() >= 0 \
           and event["endedAt"] != NO_DEADLINE_ENDEDAT:
            notice["id"] = event["id"]
            name = event["name"].replace("\n", "")
            name = name.replace("\u3000", "")
            notice["name"] = name
            # スクレイピングしたデータからurlを利用
            url = ""
            for data in web_notices:
                if event["type"] == "questCampaign" \
                   and "キャンペーン" in data["name"]:
                    if event["startedAt"] == data["begin"]:
                        url = data["url"]
                else:
                    if event["startedAt"] == data["begin"] \
                       and event["endedAt"] == data["end"]:
                        url = data["url"]
            if url != "":
                notice["url"] = url
#            notice["url"] = url
            notice["begin"] = event["startedAt"]
            notice["end"] = event["endedAt"]
            notices.append(notice)
    return notices


def main():
    # Webページを取得して解析する
    d = make_data_from_api()
    print(d)


if __name__ == '__main__':
    # オプションの解析
    parser = argparse.ArgumentParser(
                description='Image Parse for FGO Battle Results'
                )
    # 3. parser.add_argumentで受け取る引数を追加していく
    parser.add_argument('-l', '--loglevel',
                        choices=('debug', 'info'), default='info')

    args = parser.parse_args()    # 引数を解析
    logging.basicConfig(
        level=logging.INFO,
        format='%(name)s <%(filename)s-L%(lineno)s> [%(levelname)s] %(message)s',
    )
    logger.setLevel(args.loglevel.upper())

    main()
