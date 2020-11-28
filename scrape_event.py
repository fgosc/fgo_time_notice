#!/usr/bin/env python3

import argparse
import json
import logging
from datetime import datetime as dt

from chalicelib.scraper import make_notices

logger = logging.getLogger(__name__)


def main(args):
    # Webページを取得して解析する
    if args.time:
        logger.debug("use target_time")
        target_time = int(dt.strptime(args.time, "%Y/%m/%d %H:%M").timestamp())
        logger.debug("target_time: %s", target_time)
        notices = make_notices(target_time=target_time, recursive=True)
    else:
        notices = make_notices()
    data = json.dumps(notices, ensure_ascii=False)
    print(data)


if __name__ == '__main__':
    # オプションの解析
    parser = argparse.ArgumentParser(
                description='Image Parse for FGO Battle Results'
                )
    # 3. parser.add_argumentで受け取る引数を追加していく
    parser.add_argument('-t', '--time', type=str)

    parser.add_argument('-l', '--loglevel',
                        choices=('debug', 'info'), default='info')

    args = parser.parse_args()    # 引数を解析
    logging.basicConfig(
        level=logging.INFO,
        format='%(name)s <%(filename)s-L%(lineno)s> [%(levelname)s] %(message)s',
    )
    logger.setLevel(args.loglevel.upper())

    main(args)
