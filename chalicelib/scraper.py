#!/usr/bin/env python3
import argparse
import logging
import re
from datetime import datetime as dt
import dataclasses
import json
import unicodedata
from typing import List
import time

import requests
from bs4 import BeautifulSoup

ID_GEM_MIN = 6001
ID_HOLYGRAIL = 7999

logger = logging.getLogger(__name__)
quests = []

OUTPUT_FILE = "fgo_event.json"
pattern1 = r"^(?P<s_year>20[12][0-9])年(?P<s_month>[0-9]{1,2})月(?P<s_day>[0-9]{1,2})日\([日月火水木金土]\)"
pattern2 = r" (?P<s_hour>([0-9]|[01][0-9]|2[0-3])):(?P<s_min>[0-5][0-9])"
pattern3 = r"～(?P<e_month>[0-9]{1,2})月(?P<e_day>[0-9]{1,2})日\([日月火水木金土]\)"
pattern4 = r" (?P<e_hour>([01][0-9]|2[0-3])):(?P<e_min>[0-5][0-9])"
pattern = pattern1 + pattern2 + pattern3 + pattern4

def parse_distribution(url):
    """
    カルデア放送局の配信のお知らせを扱う
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

    notices = []

    # まず日付をとる
    desc = soup.select_one('span:contains("配信日時")')
    pattern1 = r"(?P<s_year>20[12][0-9])年(?P<s_month>[0-9]{1,2})月(?P<s_day>[0-9]{1,2})日"
    pattern2 = r"本配信:(?P<s_hour>([01][0-9]|2[0-3])):(?P<s_min>[0-5][0-9])～"
    for kikan in desc.next_elements:
        if kikan == "\n":
            continue
        m1 = re.search(pattern1, str(kikan))
        if m1:
            start_day = re.sub(pattern1, r"\g<s_year>/\g<s_month>/\g<s_day>", m1.group())
        m2 = re.search(pattern2, str(kikan))
        if m2:
            start_time = re.sub(pattern2, r"\g<s_hour>:\g<s_min>", m2.group())
            notice = {}
            notice["name"] = name
            notice["url"] = url
            notice["begin"] = int(dt.strptime(start_day + " " + start_time, "%Y/%m/%d %H:%M").timestamp())
            notice["end"] = None
            notices.append(notice)
            break
                    

#    logger.debug("descs: %s", descs)
    # for desc in descs:
    #     notice = {}
    #     notice["name"] = name + " イベント開催予定"
    #     notice["url"] = url
    #     notice["begin"] = None
    #     notice["end"] = None
    #     notices.append(notice)

    return notices

def parse_preview(url):
    """
    予告のお知らせを扱う
    予告なので終了時間は無し
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

    notices = []

    descs = soup.select('span:contains("イベント開催予定") ~ span.em01')
#    logger.debug("descs: %s", descs)
    for desc in descs:
        notice = {}
        notice["name"] = name + " イベント開催予定"
        notice["url"] = url
        notice["begin"] = None
        notice["end"] = None
        notice["begin_alias"] =  desc.get_text(strip=True)    
        notices.append(notice)

    return notices


def parse_campaign(url, expired_data=False):
    """
    キャンペーンのお知らせを扱う
    キャンペーン内では様々な期限のものがあるが需要が高いフレンドポイント2倍キャンペーンのみ個別抽出する
    """
    
    html = requests.get(url)
    soup = BeautifulSoup(html.content, "html.parser")
    tag_item = soup.select_one('div.title')
    title_pattern = r"(?P<title>(|｢|「).+キャンペーン)(|』)"
    t = re.search(title_pattern, tag_item.get_text())
    if t:
        logger.debug("find title")
        name = re.sub(title_pattern, r"\g<title>", t.group())
    else:
        logger.debug("not find title")
        name = tag_item.get_text()
    name = name.replace("開催", "")
    name = name.replace("【期間限定】", "")
    notices = []

    descs = soup.select('p span.em01')
#    logger.debug("descs: %s", descs)
    # 公式のキャンペーン期限を抽出
    for desc in descs:
        flag = False
        notice = {}
#        if re.search(pattern1 + pattern2 + pattern3 + pattern4, str(desc)):
        m1 = re.search(pattern, desc.get_text(strip=True))
        if m1:
            flag = True
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
                if expired_data:
                    cond = 1
                else:
                    cond = time.time() - dt.strptime(end, "%Y/%m/%d %H:%M:%S").timestamp() < 0
                if cond:
                    notice["name"] = name + " " + kikan.get_text(strip=True)
                    notice["url"] = url
                    notice["begin"] = int(dt.strptime(start, "%Y/%m/%d %H:%M:%S").timestamp())
                    notice["end"] = int(dt.strptime(end, "%Y/%m/%d %H:%M:%S").timestamp())
                    notices.append(notice)
        if flag:
            break
            # logger.info("previous_sibling: %s", desc.previous_sibling.previous_sibling.previous_sibling.previous_sibling)

    # FPCP期限を抽出
    fpcp_notice = {}
    target = soup.select_one('span:contains("をサポートに選択した場合、フレンドポイントの獲得量が2倍になります。")')
    if target is not None:
        for kikan in target.next_elements:
            if kikan == "\n":
                continue
            m1 = re.search(pattern, str(kikan))
            if m1:
                start = re.sub(pattern, r"\g<s_year>/\g<s_month>/\g<s_day> \g<s_hour>:\g<s_min>:00", m1.group())
                end = re.sub(pattern, r"\g<s_year>/\g<e_month>/\g<e_day> \g<e_hour>:\g<e_min>:59", m1.group())
                fpcp_notice["name"] = "フレンドポイント獲得量2倍キャンペーン(FPCP)"
                fpcp_notice["url"] = url
                fpcp_notice["begin"] = int(dt.strptime(start, "%Y/%m/%d %H:%M:%S").timestamp())
                fpcp_notice["end"] = int(dt.strptime(end, "%Y/%m/%d %H:%M:%S").timestamp())
                notices.append(fpcp_notice)

    # 大成功・極大成功n倍を抽出
    success_notice = {}
    target0 = soup.select_one('div:contains("下記の期間中、サーヴァントおよび概念礼装の強化をおこなった際に、大成功(経験値2倍ボーナス)･極大成功(経験値3倍ボーナス)の発生率が期間限定で")')
    target = soup.select_one('div:contains("下記の期間中、サーヴァントおよび概念礼装の強化をおこなった際に、大成功(経験値2倍ボーナス)･極大成功(経験値3倍ボーナス)の発生率が期間限定で") ~ p')
    if target is not None:
        for kikan in target.stripped_strings:
            if kikan == "\n":
                continue
            m1 = re.search(pattern, str(kikan))
            if m1:
                start = re.sub(pattern, r"\g<s_year>/\g<s_month>/\g<s_day> \g<s_hour>:\g<s_min>:00", m1.group())
                end = re.sub(pattern, r"\g<s_year>/\g<e_month>/\g<e_day> \g<e_hour>:\g<e_min>:59", m1.group())
                success_notice["name"] = "大成功･極大成功発生率n倍キャンペーン"
                success_notice["url"] = url
                success_notice["begin"] = int(dt.strptime(start, "%Y/%m/%d %H:%M:%S").timestamp())
                success_notice["end"] = int(dt.strptime(end, "%Y/%m/%d %H:%M:%S").timestamp())
                notices.append(success_notice)
    return notices


def parse_event(url, expired_data=False):
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

    notices = []

    # イベントの開催期間・交換期間を取得
    descs = soup.select('p span.em01')
#    logger.debug("descs: %s", descs)
    for desc in descs:
        notice = {}
#        if re.search(pattern1 + pattern2 + pattern3 + pattern4, str(desc)):
        m1 = re.search(pattern, desc.get_text(strip=True))
        if m1:
            start = re.sub(pattern, r"\g<s_year>/\g<s_month>/\g<s_day> \g<s_hour>:\g<s_min>:00", m1.group())
            end = re.sub(pattern, r"\g<s_year>/\g<e_month>/\g<e_day> \g<e_hour>:\g<e_min>:59", m1.group())
            year = re.sub(pattern, r"\g<s_year>", m1.group())
            # 空白にならないところまで親要素をたどる
            # お得な攻略方法獲得経験値2倍が「開催期間」としてでてくるのが冗長
            for kikan in desc.previous_siblings:
                duplicate = False
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
                if expired_data:
                    cond = 1
                else:
                    cond = time.time() - dt.strptime(end, "%Y/%m/%d %H:%M:%S").timestamp() < 0
                if cond:
                    notice["name"] = name + " " + kikan.get_text(strip=True)
                    notice["url"] = url
                    notice["begin"] = int(dt.strptime(start, "%Y/%m/%d %H:%M:%S").timestamp())
                    notice["end"] = int(dt.strptime(end, "%Y/%m/%d %H:%M:%S").timestamp())
                    for n in notices:
                        if n["name"] == notice["name"]:
                            duplicate = True
                            break
                    if not duplicate:
                        notices.append(notice)
            # logger.info("previous_sibling: %s", desc.previous_sibling.previous_sibling.previous_sibling.previous_sibling)

    # クエストの解放期間を取得
    target = soup.select_one('p:contains("【クエストの開催期間】") ~ table.trbgcolor')
    if target is None:
        return notices
    elif len(target.select('tr th')) == 2:
        for i, tar in enumerate(target.select('tr td')):
            if i % 2 == 0:
                notice = {}
                notice["name"] = name + " " + tar.get_text(strip=True) + " 解放日時"
                notice["url"] = url
            else:
                m1 = re.search(pattern, tar.get_text(strip=True))
                if m1:
                    start = re.sub(pattern, r"\g<s_year>/\g<s_month>/\g<s_day> \g<s_hour>:\g<s_min>:00", m1.group())
                    end = re.sub(pattern, r"\g<s_year>/\g<e_month>/\g<e_day> \g<e_hour>:\g<e_min>:59", m1.group())
                    if expired_data:
                        cond = 1
                    else:
                        cond = time.time() - dt.strptime(end, "%Y/%m/%d %H:%M:%S").timestamp() < 0
                    if cond:
                        notice["begin"] = int(dt.strptime(start, "%Y/%m/%d %H:%M:%S").timestamp())
                        notice["end"] = int(dt.strptime(end, "%Y/%m/%d %H:%M:%S").timestamp())
                        notices.append(notice)

    # レイドの解放期間を取得
    raid_notice = {}
    pattern0 = r"(?P<s_month>[0-9]{1,2})月(?P<s_day>[0-9]{1,2})日\([日月火水木金土]\)"

    target = soup.select_one('p:contains("イベント参加中のマスター全員で強敵に挑む、特殊な形式のクエスト")')
    if target is not None:
        m2 = re.search(pattern0 + pattern2, target.get_text(strip=True))
        if m2:
            raid_start = re.sub(pattern0 + pattern2, year + r"/\g<s_month>/\g<s_day> \g<s_hour>:\g<s_min>:00", m2.group())
            raid_notice["name"] = name + " レイド解放日時"
            raid_notice["url"] = url
            raid_notice["begin"] = int(dt.strptime(raid_start, "%Y/%m/%d %H:%M:%S").timestamp())
            raid_notice["end"] = None
            notices.append(raid_notice)
    return notices


def parse_page(load_url, expired_data=False):
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
    if "キャンペーン" in page_title or "Anniversary" in page_title:
        notices = parse_campaign(load_url, expired_data)
    elif "予告" in  page_title:
        notices = parse_preview(load_url)
    elif "配信" in  page_title:
        notices = parse_distribution(load_url)
    else:
        notices = parse_event(load_url, expired_data)
    return notices


def get_pages(url, expired_data=False):
    base_url = "https://news.fate-go.jp"
    html = requests.get(url)
    soup = BeautifulSoup(html.content, "html.parser")
    tag_item = soup.select('ul.list_news li a')
    notices = []

    for tag in tag_item:
        load_url = base_url + tag.get("href")
        logger.debug(load_url)
        event_list = parse_page(load_url, expired_data)
        if event_list is not None:
            notices += event_list
    return notices

def main():
    # Webページを取得して解析する
    news_url = "https://news.fate-go.jp"
    notices = get_pages(news_url)
    data = json.dumps(notices, ensure_ascii=False)
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
