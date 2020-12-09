#!/usr/bin/env python3
import argparse
import logging
import csv
import re
from datetime import datetime as dt
import json

logger = logging.getLogger(__name__)
csvfile = "manual.csv"
jsonfile = "manual.json"


def main():
    with open(csvfile, encoding="UTF-8") as f:
        reader = csv.DictReader(f)
        notices = [row for row in reader]

    new_notices = []
    # 時間をUNIX時間に変換
    for notice in notices:
        if notice["begin"]:
            btime = re.sub(r"\(.*?\)", "", notice["begin"])
            notice["begin"] = int(dt.strptime(btime,
                                              "%Y年%m月%d日 %H:%M").timestamp())
        if notice["end"]:
            etime = re.sub(r"\(.*?\)", "", notice["end"])
            notice["end"] = int(dt.strptime(etime,
                                            "%Y年%m月%d日 %H:%M").timestamp())
        new_notices.append(notice)

    with open(jsonfile, mode="w", encoding="UTF-8") as fout:
        fout.write(json.dumps(new_notices, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    # オプションの解析
    parser = argparse.ArgumentParser(
                description='convert csV to json'
                )
    # 3. parser.add_argumentで受け取る引数を追加していく
    parser.add_argument('-l', '--loglevel',
                        choices=('debug', 'info'), default='info')

    args = parser.parse_args()    # 引数を解析
    str_f = '%(name)s <%(filename)s-L%(lineno)s> [%(levelname)s] %(message)s'
    logging.basicConfig(
        level=logging.INFO,
        format=str_f,
    )
    logger.setLevel(args.loglevel.upper())

    main()
