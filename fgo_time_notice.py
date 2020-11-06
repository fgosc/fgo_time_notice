import time
import json
import datetime
import webbrowser
import io

from PIL import Image, ImageTk
import PySimpleGUI as sg
import requests
from bs4 import BeautifulSoup

from chalicelib.scraper import get_pages

firstfg = True
filename = './top_banner.png'
news_url = "https://news.fate-go.jp"
notices = get_pages(news_url)


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
    local_time = time.strftime('%H:%M%p')
    return local_time


def show_server_time():
    """
    日本時間を返す
    """
    jst_datetime = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    server_time = datetime.datetime.strftime(jst_datetime, '%H:%M%p')
    return server_time


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
    td_format = "{}日{}時間{}分{}秒".format(days, h, m, s)
    return td_format


def dl_banner(url):
    """
    <img alt="TOPバナー"> なイメージファイルをダウンロード
    """
    html = requests.get(url)
    soup = BeautifulSoup(html.content, "html.parser")
    tag_item = soup.select_one('img[alt="TOPバナー"]')
    base_url = "https://news.fate-go.jp"
    dl_url = base_url + tag_item["src"]
    response = requests.get(dl_url)
    with open(filename, 'wb') as savefile:
        savefile.write(response.content)    


sg.theme('Dark')

event_time = []
event_date = []
banner_dl_flag = False
for event in notices:
    if not banner_dl_flag:
        # バナーを自動取得
        current_time = time.time()
        if event["begin"] is not None and event["end"] is not None:
            if event["begin"] < current_time < event["end"]:
                dl_banner(event["url"])
                banner_dl_flag = True

    if event["begin"] is not None and "交換期間" not in event["name"]:
        event_time.append([event["name"] + " 開始", event["begin"], event["url"]])
    if event["end"] is not None:
        event_time.append([event["name"] + " 終了", event["end"], event["url"]])
    if "begin_alias" in event.keys():
        if event["begin_alias"] is not None:
            event_date.append([event["name"], event["begin_alias"], event["url"]])

event_time = sorted(event_time, key=lambda x: x[1])

event_layouts = []
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
    event_layouts.append([sg.Text(event[0], enable_events=True, key=event[2] + ' ' + str(i), font=('Helvetica', 10, 'underline')), sg.Text(size=(15, 1), key='-event_jikan' + str(i) +'-')])
for j, event in enumerate(event_date):
    event_layouts.append([sg.Text(event[0], enable_events=True, key=event[2] + ' ' + str(j + 100), font=('Helvetica', 10, 'underline')), sg.Text(event[1])])

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

layout= [
         [flame0, flame1],
         [sg.Image(data=get_img_data(filename, first=firstfg))]
         ]
layout = layout + event_layouts

window = sg.Window('FGO Time Notice',layout)

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

window.close()