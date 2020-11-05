#!/usr/bin/env python3
import argparse
import logging
import re
from datetime import datetime as dt
import dataclasses
import json
import unicodedata
from typing import List

import requests
from bs4 import BeautifulSoup

ID_GEM_MIN = 6001
ID_HOLYGRAIL = 7999

logger = logging.getLogger(__name__)
quests = []

OUTPUT_FILE = "fgo_event.json"

def parse_campaign(url):
    """
    時間関係の部分を抽出
    """
    
    html = requests.get(url)
    soup = BeautifulSoup(html.content, "html.parser")
    tag_item = soup.select_one('div.title')
    title_pattern = r"(?P<title>(｢|「).+キャンペーン)開催"
    t = re.search(title_pattern, tag_item.get_text())
    if t:
        logger.debug("find title")
        name = re.sub(title_pattern, r"\g<title>", t.group())
    else:
        logger.debug("not find title")
        name = ""

    notice = {}

    descs = soup.select('p span.em01')
#    logger.debug("descs: %s", descs)
    for desc in descs:
        pattern1 = r"^(?P<s_year>20[12][0-9])年(?P<s_month>[0-9]{1,2})月(?P<s_day>[0-9]{1,2})日\([日月火水木金土]\)"
        pattern2 = r" (?P<s_hour>([01][0-9]|2[0-3])):(?P<s_min>[0-5][0-9])"
        pattern3 = r"～(?P<e_month>[0-9]{1,2})月(?P<e_day>[0-9]{1,2})日\([日月火水木金土]\)"
        pattern4 = r" (?P<e_hour>([01][0-9]|2[0-3])):(?P<e_min>[0-5][0-9])まで"
        pattern = pattern1 + pattern2 + pattern3 + pattern4
#        if re.search(pattern1 + pattern2 + pattern3 + pattern4, str(desc)):
        m1 = re.search(pattern, desc.get_text(strip=True))
        if m1:
            start = re.sub(pattern, r"\g<s_year>/\g<s_month>/\g<s_day> \g<s_hour>:\g<s_min>:00", m1.group())
            end = re.sub(pattern, r"\g<s_year>/\g<e_month>/\g<e_day> \g<e_hour>:\g<e_min>:59", m1.group())
            # 空白にならないところまで親要素をたどる
            # お得な攻略方法獲得経験値2倍が「開催期間」としてでてくるのが冗長
            for kikan in desc.previous_siblings:
                if kikan == "\n":
                    # NavigableStringオブジェクトを操作したときのAttributeErrorを回避
                    continue
                elif kikan.get_text(strip=True) in ["", "◆","受け取り期間"]:
                    # 受け取り期間はスキップする手抜き実装
                    continue
                logger.debug(name)
                logger.debug(start)
                logger.debug(end)
                logger.debug(kikan.get_text(strip=True))
                notice[name + " " + kikan.get_text(strip=True) + " 開始"] = dt.strptime(start, "%Y/%m/%d %H:%M:%S").timestamp()
                notice[name + " " + kikan.get_text(strip=True) + " 終了"] = dt.strptime(end, "%Y/%m/%d %H:%M:%S").timestamp()
            # logger.info("previous_sibling: %s", desc.previous_sibling.previous_sibling.previous_sibling.previous_sibling)

    return notice


def parse_event(url):
    """
    時間関係の部分を抽出
    """
    
    html = requests.get(url)
    soup = BeautifulSoup(html.content, "html.parser")
    tag_item = soup.select_one('div.title')
    title_pattern = r"(｢|「)(?P<title>.+)(｣|」)"
    t = re.search(title_pattern, tag_item.get_text())
    if t:
        logger.debug("find title")
        name = re.sub(title_pattern, r"\g<title>", t.group())
    else:
        logger.debug("not find title")
        name = ""

    notice = {}

    descs = soup.select('p span.em01')
#    logger.debug("descs: %s", descs)
    for desc in descs:
        pattern1 = r"^(?P<s_year>20[12][0-9])年(?P<s_month>[0-9]{1,2})月(?P<s_day>[0-9]{1,2})日\([日月火水木金土]\)"
        pattern2 = r" (?P<s_hour>([01][0-9]|2[0-3])):(?P<s_min>[0-5][0-9])"
        pattern3 = r"～(?P<e_month>[0-9]{1,2})月(?P<e_day>[0-9]{1,2})日\([日月火水木金土]\)"
        pattern4 = r" (?P<e_hour>([01][0-9]|2[0-3])):(?P<e_min>[0-5][0-9])まで"
        pattern = pattern1 + pattern2 + pattern3 + pattern4
#        if re.search(pattern1 + pattern2 + pattern3 + pattern4, str(desc)):
        m1 = re.search(pattern, desc.get_text(strip=True))
        if m1:
            start = re.sub(pattern, r"\g<s_year>/\g<s_month>/\g<s_day> \g<s_hour>:\g<s_min>:00", m1.group())
            end = re.sub(pattern, r"\g<s_year>/\g<e_month>/\g<e_day> \g<e_hour>:\g<e_min>:59", m1.group())
            # 空白にならないところまで親要素をたどる
            # お得な攻略方法獲得経験値2倍が「開催期間」としてでてくるのが冗長
            for kikan in desc.previous_siblings:
                if kikan == "\n":
                    # NavigableStringオブジェクトを操作したときのAttributeErrorを回避
                    continue
                elif kikan.get_text(strip=True) in ["", "◆", "開催期間"]:
                    # 開催期間は配布鯖経験値2倍期間をスキップする手抜き実装
                    continue
                logger.debug(name)
                logger.debug(start)
                logger.debug(end)
                logger.debug(kikan.get_text(strip=True))
                notice[name + " " + kikan.get_text(strip=True) + " 開始"] = dt.strptime(start, "%Y/%m/%d %H:%M:%S").timestamp()
                notice[name + " " + kikan.get_text(strip=True) + " 終了"] = dt.strptime(end, "%Y/%m/%d %H:%M:%S").timestamp()
            # logger.info("previous_sibling: %s", desc.previous_sibling.previous_sibling.previous_sibling.previous_sibling)

    return notice


def parse_page(load_url):
    html = requests.get(load_url)
    soup = BeautifulSoup(html.content, "html.parser")
    page_title = soup.find(
                    'title'
                    ).text.replace(
                    "  |  Fate/Grand Order 公式サイト", ""
                    )
    for word in ["TIPS"
                 "重要", "交換可能なアイテムについて",
                ]:
        if word in page_title:
            return None
    if "キャンペーン" in page_title:
        notice = parse_campaign(load_url)
    else:
        notice = parse_event(load_url)
    return notice


def get_pages(url):
    base_url = "https://news.fate-go.jp"
    html = requests.get(url)
    soup = BeautifulSoup(html.content, "html.parser")
    tag_item = soup.select('ul.list_news li a')
    notice = {}

    for tag in tag_item:
        load_url = base_url + tag.get("href")
        logger.debug(load_url)
        dic = parse_page(load_url)
        if dic is not None:
            notice.update(dic)
    notice = sorted(notice.items(), key=lambda x:x[1])
    return notice

def main():
    # Webページを取得して解析する
    news_url = "https://news.fate-go.jp"
    notice = get_pages(news_url)
    data = json.dumps(notice, ensure_ascii=False)
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
