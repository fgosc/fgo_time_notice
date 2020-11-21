#!/usr/bin/env python3
import argparse
import logging
import re
from datetime import datetime as dt
import json
import time

import requests
from bs4 import BeautifulSoup

from chalicelib.api_data import make_data_from_api

ID_GEM_MIN = 6001
ID_HOLYGRAIL = 7999

logger = logging.getLogger(__name__)
quests = []

OUTPUT_FILE = "fgo_event.json"
pattern1 = r"(?P<s_year>20[12][0-9])年(?P<s_month>[0-9]{1,2})月(?P<s_day>[0-9]{1,2})日\([日月火水木金土]\)"
pattern2 = r"(?P<s_hour>([0-9]|[01][0-9]|2[0-3])):(?P<s_min>[0-5][0-9])"
pattern3 = r"(?P<e_month>[0-9]{1,2})月(?P<e_day>[0-9]{1,2})日\([日月火水木金土]\)"
pattern4 = r"(?P<e_hour>([0-9]|[01][0-9]|2[0-3])):(?P<e_min>[0-5][0-9])"
pattern = pattern1 + " " + pattern2 + "～" + pattern3 + " " + pattern4
pattern_sameday = pattern1 + " " + pattern2 + "～" + pattern4
pattern_undefine = pattern1 + " " + pattern2 + "～" + "未定"


def parse_maintenance(url, expired_data=False):
    """
    メンテナンスを扱う
    """

    html = requests.get(url)
    soup = BeautifulSoup(html.content, "html.parser")
    tag_item = soup.select_one('div.title')
    if "臨時" in tag_item.get_text():
        name = "臨時メンテナンス"
    elif "緊急" in tag_item.get_text():
        name = "緊急メンテナンス"
    else:
        name = "メンテナンス"

    notices = []
    if "終了" in tag_item.get_text():
        return notices
    str_np = 'p:contains("「Fate/Grand Order」をプレイすることができません")'
    cant_play = soup.select_one(str_np)
    if cant_play is None:
        return notices

    # まず日付をとる
    desc = soup.select_one('span.headline:contains("日時")')
    for kikan in desc.next_elements:
        if kikan == "\n":
            continue
        # 通常の13-18時メンテナンス用
        m1 = re.search(pattern_sameday, str(kikan))
        if m1:
            str_s = r"\g<s_year>/\g<s_month>/\g<s_day> \g<s_hour>:\g<s_min>"
            start = re.sub(pattern_sameday, str_s, m1.group())
            str_e = r"\g<s_year>/\g<s_month>/\g<s_day> \g<e_hour>:\g<e_min>"
            end = re.sub(pattern_sameday, str_e, m1.group())
            notice = {}
            notice["name"] = name
            notice["url"] = url
            notice["begin"] = int(
                                  dt.strptime(
                                              start,
                                              "%Y/%m/%d %H:%M").timestamp()
                                  )
            notice["end"] = int(dt.strptime(end, "%Y/%m/%d %H:%M").timestamp())
            notice["type"] = "maintenance"
            notices.append(notice)
            break
        # 日付をまたぐメンテナンス用(発生頻度: 超レア)
        m2 = re.search(pattern, str(kikan))
        if m2:
            str_s2 = r"\g<s_year>/\g<s_month>/\g<s_day> \g<s_hour>:\g<s_min>"
            start = re.sub(pattern, str_s2, m2.group())
            str_e2 = r"\g<s_year>/\g<s_month>/\g<e_day> \g<e_hour>:\g<e_min>"
            end = re.sub(pattern, str_e2, m2.group())
            notice = {}
            notice["name"] = name
            notice["url"] = url
            notice["begin"] = int(dt.strptime(
                                              start,
                                              "%Y/%m/%d %H:%M"
                                              ).timestamp())
            notice["end"] = int(dt.strptime(end, "%Y/%m/%d %H:%M").timestamp())
            notice["type"] = "maintenance"
            notices.append(notice)
            break

        # 緊急メンテナンス
        m3 = re.search(pattern_undefine, str(kikan))
        if m3:
            str_s3 = r"\g<s_year>/\g<s_month>/\g<s_day> \g<s_hour>:\g<s_min>"
            start = re.sub(pattern_undefine, str_s3, m3.group())
            notice = {}
            notice["name"] = name
            notice["url"] = url
            notice["begin"] = int(dt.strptime(
                                              start,
                                              "%Y/%m/%d %H:%M").timestamp())
            notice["end"] = None
            notice["type"] = "maintenance"
            notices.append(notice)
            break

    return notices


def parse_broadcast(url):
    """
    カルデア放送局の配信のお知らせを扱う
    開始時間しかないので放送が始まったら出力しない
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
            str_sd = r"\g<s_year>/\g<s_month>/\g<s_day>"
            sday = re.sub(pattern1, str_sd, m1.group())
        m2 = re.search(pattern2, str(kikan))
        if m2:
            stime = re.sub(pattern2, r"\g<s_hour>:\g<s_min>", m2.group())
            day_time = dt.strptime(sday + " " + stime, "%Y/%m/%d %H:%M")
            day_time_f = int(day_time.timestamp())
            # cond = time.time() - day_time_f < 0
            # if cond:
            #     notice = {}
            #     notice["name"] = name
            #     notice["url"] = url
            #     str_b = dt.strptime(sday + " " + stime, "%Y/%m/%d %H:%M")
            #     notice["begin"] = int(str_b.timestamp())
            #     notice["end"] = None
            #     notice["type"] = "broadcast"
            #     notices.append(notice)
            notice = {}
            notice["name"] = name
            notice["url"] = url
            str_b = dt.strptime(sday + " " + stime, "%Y/%m/%d %H:%M")
            notice["begin"] = int(str_b.timestamp())
            notice["end"] = None
            notice["type"] = "broadcast"
            notices.append(notice)

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
        notice["begin_alias"] = desc.get_text(strip=True)
        notice["type"] = "eventQuest"
        notices.append(notice)

    return notices


def parse_campaign(url, expired_data=False):
    """
    キャンペーンのお知らせを扱う
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
        flag = False  # 重複チェック
        notice = {}
#        if re.search(pattern1 + pattern2 + pattern3 + pattern4, str(desc)):
        m1 = re.search(pattern, desc.get_text(strip=True))
        if m1:
            flag = True
            str_s = r"\g<s_year>/\g<s_month>/\g<s_day> \g<s_hour>:\g<s_min>:00"
            start = re.sub(pattern, str_s, m1.group())
            str_e = r"\g<s_year>/\g<e_month>/\g<e_day> \g<e_hour>:\g<e_min>:59"
            end = re.sub(pattern, str_e, m1.group())
            # 空白にならないところまで親要素をたどる
            # お得な攻略方法獲得経験値2倍が「開催期間」としてでてくるのが冗長
            for kikan in desc.previous_siblings:
                if kikan == "\n":
                    # NavigableStringオブジェクトを操作したときのAttributeErrorを回避
                    continue
                elif kikan.get_text(strip=True) in ["", "◆", "受け取り期間"]:
                    # 受け取り期間はスキップする手抜き実装
                    continue
                logger.debug(name)
                logger.debug(start)
                logger.debug(end)
                logger.debug(kikan.get_text(strip=True))
                # if expired_data:
                #     cond = 1
                # else:
                #     end_t = dt.strptime(end, "%Y/%m/%d %H:%M:%S").timestamp()
                #     cond = time.time() - end_t < 0
                # if cond:
                #     notice["name"] = name + " " + kikan.get_text(strip=True)
                #     notice["url"] = url
                #     begin_t = dt.strptime(start, "%Y/%m/%d %H:%M:%S")
                #     notice["begin"] = int(begin_t.timestamp())
                #     end_t = dt.strptime(end, "%Y/%m/%d %H:%M:%S")
                #     notice["end"] = int(end_t.timestamp())
                #     notices.append(notice)
                notice["name"] = name + " " + kikan.get_text(strip=True)
                notice["url"] = url
                begin_t = dt.strptime(start, "%Y/%m/%d %H:%M:%S")
                notice["begin"] = int(begin_t.timestamp())
                end_t = dt.strptime(end, "%Y/%m/%d %H:%M:%S")
                notice["end"] = int(end_t.timestamp())
                notice["type"] = "campaign"
                notices.append(notice)
        if flag:
            break

        m2 = re.search(pattern_sameday, desc.get_text(strip=True))
        if m2:
            flag = True
            start_s = r"\g<s_year>/\g<s_month>/\g<s_day> \g<s_hour>:\g<s_min>:00"
            start = re.sub(pattern_sameday, start_s, m2.group())
            end_s = r"\g<s_year>/\g<s_month>/\g<s_day> \g<e_hour>:\g<e_min>:59"
            end = re.sub(pattern_sameday, end_s, m2.group())
            # 空白にならないところまで親要素をたどる
            # お得な攻略方法獲得経験値2倍が「開催期間」としてでてくるのが冗長
            for kikan in desc.previous_siblings:
                if kikan == "\n":
                    # NavigableStringオブジェクトを操作したときのAttributeErrorを回避
                    continue
                elif kikan.get_text(strip=True) in ["", "◆", "受け取り期間"]:
                    # 受け取り期間はスキップする手抜き実装
                    continue
                logger.debug(name)
                logger.debug(start)
                logger.debug(end)
                logger.debug(kikan.get_text(strip=True))
                # if expired_data:
                #     cond = 1
                # else:
                #     cond = time.time() - dt.strptime(
                #                                      end,
                #                                      "%Y/%m/%d %H:%M:%S"
                #                                      ).timestamp() < 0
                # if cond:
                #     notice["name"] = name + " " + kikan.get_text(strip=True)
                #     notice["url"] = url
                #     begin_s = dt.strptime(start, "%Y/%m/%d %H:%M:%S")
                #     notice["begin"] = int(begin_s.timestamp())
                #     end_s = dt.strptime(end, "%Y/%m/%d %H:%M:%S")
                #     notice["end"] = int(end_s.timestamp())
                #     notices.append(notice)
                notice["name"] = name + " " + kikan.get_text(strip=True)
                notice["url"] = url
                begin_s = dt.strptime(start, "%Y/%m/%d %H:%M:%S")
                notice["begin"] = int(begin_s.timestamp())
                end_s = dt.strptime(end, "%Y/%m/%d %H:%M:%S")
                notice["end"] = int(end_s.timestamp())
                notice["type"] = "campaign"
                notices.append(notice)
        if flag:
            break

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
                elif kikan.get_text(strip=True) in ["", "◆", "開催期間", "受け取り期間"]:
                    # 開催期間は配布鯖経験値2倍期間をスキップする手抜き実装
                    # 受け取り期間はログインボーナスをスキップする手抜き実装
                    continue
                logger.debug(name)
                logger.debug(start)
                logger.debug(end)
                logger.debug(kikan.get_text(strip=True))
                # if expired_data:
                #     cond = 1
                # else:
                #     if kikan.get_text(strip=True) == "イベント開催期間":
                #         s_time = dt.strptime(start, "%Y/%m/%d %H:%M:%S")
                #         if time.time() - s_time.timestamp() > 0:
                #             continue
                #     e_time = dt.strptime(end, "%Y/%m/%d %H:%M:%S")
                #     cond = time.time() - e_time.timestamp() < 0
                # if cond:
                #     notice["name"] = name + " " + kikan.get_text(strip=True)
                #     notice["url"] = url
                #     begin_dt = dt.strptime(start, "%Y/%m/%d %H:%M:%S")
                #     notice["begin"] = int(begin_dt.timestamp())
                #     end_dt = dt.strptime(end, "%Y/%m/%d %H:%M:%S")
                #     notice["end"] = int(end_dt.timestamp())
                #     for n in notices:
                #         if n["name"] == notice["name"] \
                #            and n["end"] == notice["end"]:
                #             duplicate = True
                #             break
                #     if not duplicate:
                #         notices.append(notice)
                notice["name"] = name + " " + kikan.get_text(strip=True)
                notice["url"] = url
                begin_dt = dt.strptime(start, "%Y/%m/%d %H:%M:%S")
                notice["begin"] = int(begin_dt.timestamp())
                end_dt = dt.strptime(end, "%Y/%m/%d %H:%M:%S")
                notice["end"] = int(end_dt.timestamp())
                notice["type"] = "eventQuest"
                for n in notices:
                    if n["name"] == notice["name"] \
                        and n["end"] == notice["end"]:
                        duplicate = True
                        break
                if not duplicate:
                    notices.append(notice)

    # クエストの解放期間を取得
    # 解放期間が直近のクエスト一つを出すよう変更
    target = soup.select_one('p:contains("【クエストの開催期間】") ~ table.trbgcolor')
    if target is None:
        return notices
    elif len(target.select('tr th')) == 2:
        for i, tar in enumerate(target.select('tr td')):
            if i % 2 == 0:
                notice = {}
                # クエスト名の改行を replace 処理で
                tar_text = tar.get_text(strip=True)
                if not tar_text.startswith("フリークエスト"):
                    tar_text = tar_text.replace("フリークエスト", "・フリークエスト")
                if not tar_text.startswith("閑話"):
                    tar_text = tar_text.replace("閑話", "・閑話")
                notice["name"] = name + " " + tar_text + " 解放"
                notice["url"] = url
            else:
                m1 = re.search(pattern, tar.get_text(strip=True))
                if m1:
                    start_p = r"\g<s_year>/\g<s_month>/\g<s_day> \g<s_hour>:\g<s_min>:00"
                    start = re.sub(pattern, start_p, m1.group())
                    end_p = r"\g<s_year>/\g<e_month>/\g<e_day> \g<e_hour>:\g<e_min>:59"
                    end = re.sub(pattern, end_p, m1.group())
                    # if expired_data:
                    #     cond = 1
                    # else:
                    #     end_t = dt.strptime(end, "%Y/%m/%d %H:%M:%S")
                    #     cond = time.time() - end_t.timestamp() < 0
                    # if cond:
                    #     start_t = dt.strptime(start, "%Y/%m/%d %H:%M:%S")
                    #     cond2 = time.time() - start_t.timestamp() < 0
                    #     if cond2:
                    #         begin_s = dt.strptime(start, "%Y/%m/%d %H:%M:%S")
                    #         notice["begin"] = int(begin_s.timestamp())
                    #         end_s = dt.strptime(end, "%Y/%m/%d %H:%M:%S")
                    #         notice["end"] = int(end_s.timestamp())
                    #         notices.append(notice)
                    #         break
                    start_t = dt.strptime(start, "%Y/%m/%d %H:%M:%S")
                    cond2 = time.time() - start_t.timestamp() < 0
                    if cond2:
                        begin_s = dt.strptime(start, "%Y/%m/%d %H:%M:%S")
                        notice["begin"] = int(begin_s.timestamp())
                        end_s = dt.strptime(end, "%Y/%m/%d %H:%M:%S")
                        notice["end"] = int(end_s.timestamp())
                        notice["type"] = "eventQuest"
                        notices.append(notice)
                        break

    # レイドの解放期間を取得
    raid_notice = {}
    pattern0 = r"(?P<s_month>[0-9]{1,2})月(?P<s_day>[0-9]{1,2})日\([日月火水木金土]\)"

    target = soup.select_one('p:contains("イベント参加中のマスター全員で強敵に挑む、特殊な形式のクエスト")')
    if target is not None:
        m2 = re.search(pattern0 + pattern2, target.get_text(strip=True))
        if m2:
            rs_str = r"/\g<s_month>/\g<s_day> \g<s_hour>:\g<s_min>:00"
            rs_ptn = year + rs_str
            raid_start = re.sub(pattern0 + pattern2, rs_ptn, m2.group())
            raid_notice["name"] = name + " レイド解放日時"
            raid_notice["url"] = url
            begin_s = dt.strptime(raid_start, "%Y/%m/%d %H:%M:%S")
            raid_notice["begin"] = int(begin_s.timestamp())
            raid_notice["end"] = None
            raid_notice["type"] = "eventQuest"

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
                 "重要",
                 "交換可能なアイテムについて",
                 "召喚"
                 ]:
        if word in page_title:
            return None
    if "キャンペーン" in page_title or "Anniversary" in page_title:
        notices = parse_campaign(load_url, expired_data)
    elif "予告" in page_title:
        notices = parse_preview(load_url)
    elif "配信" in page_title:
        if "発表" in page_title:
            return {}
        else:
            notices = parse_broadcast(load_url)
    elif "メンテナンス" in page_title:
        notices = parse_maintenance(load_url)
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
        try:
            event_list = parse_page(load_url, expired_data)
        except Exception as e:
            logger.exception(e)
            event_list = None
        if event_list is not None:
            notices += event_list
    return notices


def expired_notice(notices):
    new_notices = []
    for notice in notices:
        # 終了時間が過ぎた項目はカット
        if notice["end"] is not None:
            if notice["end"] < int(time.time()):
                continue
        if notice["type"] == "broadcast" \
           and notice["begin"] < int(time.time()):
            continue
        if notice["type"] == "eventQuest" \
           and "イベント開催期間" in notice["name"] \
           or "解放" in notice["name"] \
           and notice["begin"] < int(time.time()):
           # APIからのデータと重複するため
            continue
        if notice["type"] == "campaign" \
           and notice["begin"] < int(time.time()):
           # APIからのデータと重複するため
            continue
        new_notices.append(notice)
    return new_notices


def make_notices():
    # Webページを取得して解析する
    news_url = "https://news.fate-go.jp"
    maintenance_url = "https://news.fate-go.jp/maintenance"
    notices_n = get_pages(news_url)
    notices_m = get_pages(maintenance_url)
#    notices_e = get_pages(news_url, expired_data=True)
    notices_a = make_data_from_api(notices_n)
    notices_e = expired_notice(notices_n + notices_m)
    return notices_e + notices_a


def main():
    notices = make_notices()
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
    str_f = '%(name)s <%(filename)s-L%(lineno)s> [%(levelname)s] %(message)s'
    logging.basicConfig(
        level=logging.INFO,
        format=str_f,
    )
    logger.setLevel(args.loglevel.upper())

    main()
