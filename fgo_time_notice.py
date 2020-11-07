#!/usr/bin/env python3
import time
import json
import datetime
import webbrowser
import io
import requests

from PIL import Image, ImageTk
import PySimpleGUI as sg
import requests
from bs4 import BeautifulSoup

from chalicelib.scraper import get_pages

firstfg = True
filename = './top_banner.png'
news_url = "https://news.fate-go.jp"
maintenance_url = "https://news.fate-go.jp/maintenance"
json_url = "https://fgojunks.max747.org/timer/assets/events.json"
dl_banner_url = ""

def update_data():
    """
    定期更新実装のため関数化
    新しいレイアウトを作成する必要がある場合は、探しているレイアウトで新しいウィンドウを作成し、もう一方のウィンドウを閉じます。
    """
    r_get = requests.get(json_url)
    notices = r_get.json()
    return notices
# # dataを自身で作成 起動速度は遅い
# notices_n = get_pages(news_url)
# notices_m = get_pages(maintenance_url)
# notices = notices_n + notices_m


def get_img_data(f, maxsize=(800, 300), first=False):
    """Generate image data using PIL."""
    global status_text
    im = Image.open(f)
    status_text = "%d x %d" % im.size  # original image size
    im.thumbnail(maxsize)
    status_text += " (%d x %d)" % im.size  # thumbnail image size
    if first:
        bio = io.BytesIO()
        im.save(bio, format="PNG")
        del im
        return bio.getvalue()
    return ImageTk.PhotoImage(im)


def get_h_m_s(td):
    m, s = divmod(td.seconds, 60)
    h, m = divmod(m, 60)
    return h, m, s


def show_local_time():
    local_time = time.strftime('%I:%M%p')
    return local_time


def show_server_time():
    """
    日本時間を返す
    """
    jst_datetime = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    server_time = datetime.datetime.strftime(jst_datetime, '%I:%M%p')
    return server_time


def local_to_jst(timestamp_local):
    datetime_local = datetime.datetime.strptime("2015-07-30 " + timestamp_local, "%Y-%m-%d %H:%M")
    datetime_jst = datetime_local.astimezone(datetime.timezone(datetime.timedelta(hours=+9)))
    timestamp_jst = datetime.datetime.strftime(datetime_jst, '%H:%M')
    return timestamp_jst


def show_event_time(event_time):
    etime = datetime.datetime.fromtimestamp(event_time)
    ntime = datetime.datetime.now()
    td = etime - ntime
    if td.total_seconds() < 0:
        days = 0
        h = m = s = 0
    else:
        days = td.days
        h, m, s = get_h_m_s(td)
    # 形式を整える
    td_format = "{days}日{hour:02}時間{minutes:02}分{second:02}秒".format(days=days, hour=h, minutes=m, second=s)
    return td_format


def dl_banner(url):
    """
    <img alt="TOPバナー"> なイメージファイルをダウンロード
    """
    global dl_banner_url
    if url == dl_banner_url:
        return
    html = requests.get(url)
    soup = BeautifulSoup(html.content, "html.parser")
    tag_item = soup.select_one('img[alt="TOPバナー"]')
    base_url = "https://news.fate-go.jp"
    dl_url = base_url + tag_item["src"]
    response = requests.get(dl_url)
    with open(filename, 'wb') as savefile:
        savefile.write(response.content)
    dl_banner_url = url   

def make_window(location=None):
    notices = update_data()
    sg.theme('Dark')

    event_time = []
    event_date = []
    next_quest_open = []
    banner_dl_flag = False
    current_time = time.time()
    for event in notices:
        if not banner_dl_flag:
            # バナーを自動取得
            if event["begin"] is not None and event["end"] is not None:
                if event["begin"] < current_time < event["end"]:
                    dl_banner(event["url"])
                    banner_dl_flag = True

        if event["end"] is not None:
            if event["end"] < current_time:
                continue

        # クエスト解放日時のロジックは解放されていない最新のクエストのみ表示する
        # 同じイベントのクエスト解放日時は古いほうからデータに入っている前提
        if "レイド解放日時" in event["name"]:
            # もし解放日時がすでにすぎていたら無視
            if event["begin"] < current_time:
                continue
            event_time.append([event["name"], event["begin"], event["url"]])
        elif "解放日時" in event["name"]:
            # もし解放日時がすでにすぎていたら無視
            if event["begin"] < current_time:
                continue
            event_names = event["name"].split(" ")
            if event_names[0] not in next_quest_open:
                event_time.append([event["name"], event["begin"], event["url"]])
                next_quest_open.append(event_names[0])
                continue
        if event["begin"] is not None and "交換期間" not in event["name"]:
            event_time.append([event["name"] + " 開始", event["begin"], event["url"]])
        if event["end"] is not None and "解放日時" not in event["name"]:
            event_time.append([event["name"] + " 終了", event["end"], event["url"]])
        if "begin_alias" in event.keys():
            if event["begin_alias"] is not None:
                event_date.append([event["name"], event["begin_alias"], event["url"]])

    event_time = sorted(event_time, key=lambda x: x[1])

    event_title_f = []
    event_time_f = []
    for i, event in enumerate(event_time):
        etime = datetime.datetime.fromtimestamp(event[1])
        ntime = datetime.datetime.now()
        td = etime - ntime
        if td.total_seconds() < 0:
            days = 0
            h = m = s = 0
        else:
            days = td.days
            h, m, s = get_h_m_s(td)
        # 形式を整える
        td_format = "{}日{}時間{}分{}秒".format(days, h, m, s)
        # event_layouts.append([sg.Text(event[0], enable_events=True, key=event[2] + ' ' + str(i), font=('Helvetica', 10, 'underline')), sg.Text(size=(16, 1), key='-event_jikan' + str(i) +'-')])
        event_title_f.append([sg.Text(event[0], enable_events=True, key=event[2] + ' ' + str(i), font=('Helvetica', 10, 'underline'))])
        event_time_f.append([sg.Text(size=(16, 1), justification='right', key='-event_jikan' + str(i) +'-')])
    for j, event in enumerate(event_date):
        event_title_f.append([sg.Text(event[0], enable_events=True, key=event[2] + ' ' + str(j + 100), font=('Helvetica', 10, 'underline'))])
        event_time_f.append([sg.Text(event[1], size=(16, 1), justification='right')])

    flame_title = sg.Frame("", event_title_f, relief="flat")
    flame_time = sg.Frame("", event_time_f, relief="flat")
    flame0 = sg.Frame("local",
                    [
                    [sg.Text(size=(8, 1), font=('Helvetica', 20), justification='center', key='-local_time-')]
                    ],
                    title_location=sg.TITLE_LOCATION_TOP, relief="flat", pad=((125,125),(0,0))
                    )

    flame1 = sg.Frame("Server",
                    [
                    [sg.Text(size=(8, 1), font=('Helvetica', 20), justification='center', key='-server_time-')]
                    ],
                    title_location=sg.TITLE_LOCATION_TOP, relief="flat", pad=((125,125),(0,0))
                    )

    t1 = sg.Tab("イベント", [
            [flame_title, flame_time],
            [sg.Button("データ更新", key='-update-')]
            ])

    time_list = [["00:00", "デイリーミッション/曜日クエスト/FP召喚リセット"],
         ["04:00",	"デイリーログインリセット"],
         ["13:00",	"イベント終了/メンテナンス開始"],
         ["18:00",	"イベント開始/メンテナンス終了"]]
    T = [[local_to_jst(item[0]), item[0] + " JST", item[1]] for item in time_list]

    # T = [["09:00", "00:00 JST", "デイリーミッション/曜日クエスト/FP召喚リセット"],
    #      ["13:00", "04:00 JST",	"デイリーログインリセット"],
    #      ["17:00", "13:00 JST",	"イベント終了/メンテナンス開始"],
    #      ["17:00", "18:00 JST",	"イベント開始/メンテナンス終了"]]
    H = ["Local Time", "Server Time", "項目"]
    t2 = sg.Tab("タイムテーブル", [[sg.Table(T,headings=H,
        auto_size_columns=False,
        col_widths=[20,20,50],
        max_col_width=50,
        hide_vertical_scroll=True,
        num_rows=4,
        justification="center",
        display_row_numbers=False,
        )]])
#         row_colors=((0,'white', 'black'),(1,'white', 'black'),(2,'white', 'black'),(3,'white', 'black'))),

    layout = [
              [flame0, flame1],
              [sg.Image(data=get_img_data(filename, first=firstfg))],
              [sg.TabGroup([[t1, t2]])]]
    # layout = layout + flame_list

    if location is None:
       w = sg.Window('FGO Time Notice', layout)
    else:
       w = sg.Window('FGO Time Notice', layout, location=location)
    return w, event_time

window, event_time = make_window()

while True:
    event, values = window.read(timeout=100,timeout_key='-timeout-')
    #timeoutを指定することで、timeoutイベントが起こります。timeoutの単位はたぶんms
    # print(event,values)
    #↑コメントアウトを外すと、どんなイベントが起こっているか確かめることができます。
    
    if event in (None,):
        break
    elif event in '-timeout-':
        local_time = show_local_time()
        server_time = show_server_time()
        window['-local_time-'].update(local_time)
        window['-server_time-'].update(server_time)
        for i in range(len(event_time)):
            event_jikan = show_event_time(event_time[i][1])
            window['-event_jikan' + str(i) + '-'].update(event_jikan)
    elif event.startswith("http"):
        tmp = event.split(' ')
        webbrowser.open(tmp[0])
    elif event in '-update-':
        location = window.CurrentLocation()
        window.close()
        window, event_time = make_window(location)

window.close()
