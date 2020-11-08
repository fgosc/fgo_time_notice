#!/usr/bin/env python3

import argparse
import json
import logging

from chalicelib.scraper import get_pages

logger = logging.getLogger(__name__)


def main():
    # Webページを取得して解析する
    news_url = "https://news.fate-go.jp"
    maintenance_url = "https://news.fate-go.jp/maintenance"
    notices_n = get_pages(news_url)
    notices_m = get_pages(maintenance_url)
    data = json.dumps(notices_n + notices_m, ensure_ascii=False)
    print(data)


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
