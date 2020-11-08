# fgo_time_notice
![image](https://cdn.discordapp.com/attachments/734720750862467076/774586824449589258/unknown.png)

## 概要
Fate Grand/Order のお知らせに関する時刻をJSON形式で取得する

[FGO time](https://www.mitsunee.com/fgo/time/)　の日本語版サポートが無くなってしまったのでアイデアを参考にしつつ同様な機能を持つものの作成を目指したもの

- 実装:API [events.json](https://fgojunks.max747.org/timer/assets/events.json)
- 上記を使ったアプリ版: fgo_time_notice.py
- 上記を使ったWEB版: [FGO Timer](https://fgojunks.max747.org/timer/)

## 仕様
```
$ python scrape_event.py
```
でFate Grand/Orderのお知らせから時間に関する情報をJSON形式で出力します

取得するお知らせは以下の通りです
- イベント
- キャンペーン
  - フレンドポイント獲得量2倍キャンペーン(FPCP)
  - 大成功・極大成功n倍
- メンテナンス
- カルデア放送局放送時間

----
## fgo_time_notice.py の使い方
### 概要
[FGO time](https://www.mitsunee.com/fgo/time/)の日本版FGO対応クローンのようなアプリです

### インストール
※ Windows の場合、Packageから実行ファイルをZIPで取得できます

```
$ pip install -r requirements_tn.txt
```

### 起動
```
$ python fgo_time_notice.py
```
### 使い方
- 項目をクリックするとブラウザで該当するリンクが開かれます
- 「データ更新」ボタンを押すとAPIからデータを取得して情報更新します
