import requests
from bs4 import BeautifulSoup
import time
import csv
from urllib.parse import urljoin, urlparse

# トップページのurl
base_url = 'https://www.musashino-u.ac.jp'
domain = urlparse(base_url).netloc

# データを格納する変数
site_map = {}       # タイトルを保存
visited_urls = set() # 既にアクセスしたURLを記録
urls_to_visit = [base_url] # これからアクセスするURLのリスト(訪問予定リスト)

# 上限を設定(無限ループにハマった時用に設置)
MAX_PAGES = 10000 
# 正常に取得し、CSVファイルに情報を書き込むことができたページ数
crawled_count = 0

print("クローリングを開始します...")

# URLが残ってるかつ、クローリング上限に達してない場合ループをする
while urls_to_visit and crawled_count < MAX_PAGES:
    # 訪問予定リストの一番上を消す
    current_url = urls_to_visit.pop(0)

    # 取り出したURLが訪問済みリストにある場合は、以降の処理をやめる
    if current_url in visited_urls:
        continue

    # 現在どこにアクセスしているかターミナルに表示
    print(f"[{crawled_count + 1}] アクセス中: {current_url}")
    
    try:
        # current_urlに入っているURLにアクセスしてWebページのデータを取得する。
        # 10秒以内に応答がない場合はエラーとして扱う
        res = requests.get(current_url, timeout=10)
        visited_urls.add(current_url) # 訪問済みに記録
        
        # サーバーへの負荷軽減のため1秒停止する
        time.sleep(1)

        # 取得した情報からURLのコンテンツタイプ（HTML、PDFなど）を取得
        content_type = res.headers.get('Content-Type', '').lower()

        # PDFファイルの場合の処理
        if 'application/pdf' in content_type or current_url.lower().endswith('.pdf'):
            filename = current_url.split('/')[-1] # URLを"/"で区切り、末尾ファイルだけ抽出する
            site_map[current_url] = f"[PDF] {filename}" #PDFはタイトルがないため、代わりに"[PDF]ファイル名.pdf"を入れる
            crawled_count += 1 #クロール数を1増やす
            continue # PDFの中にHTMLリンクはないので、次のURLへ進む

        # HTML以外のファイル（画像など）はスキップ
        if 'text/html' not in content_type:
            continue

        # 文字化け防止
        res.encoding = res.apparent_encoding
        # ダウンロードしたhtmlを変換
        soup = BeautifulSoup(res.text, 'html.parser')

        title_tag = soup.find('title') # titleタグを探し出す
        title = title_tag.text.strip() if title_tag else "No Title" # タイトルがある場合文字を入れる(ない場合はNo Titleを入れる)
        site_map[current_url] = title
        crawled_count += 1 # クロールを1増やす

        # ページ内のすべてのaタグを抽出して訪問リストに追加
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']

            # 省略されたページを完全なURLに修復
            full_url = urljoin(current_url, href)
            full_url = full_url.split('#')[0] # ページ内リンク削除

            parsed_url = urlparse(full_url)
            
            # 同一ドメイン内のURLかチェック
            if parsed_url.netloc == domain:
                # まだ訪問しておらず、予定リストにもURLが入っていない場合
                if full_url not in visited_urls and full_url not in urls_to_visit:
                    # 画像やZIPのみ除外する
                    if not full_url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.zip')):
                        urls_to_visit.append(full_url)
    # 通信エラーやタイムアウトが起きた時はスキップをする
    except requests.exceptions.RequestException as e:
        print(f"  通信エラー発生（スキップします）: {e}")
        # 今アクセスしているURLを訪問済みリストに追加
        visited_urls.add(current_url) 

print(f"\n合計 {crawled_count} 個のURL情報を取得しました。")

# 辞書型変数をCSVファイルに保存
csv_filename = 'musashino_sitemap.csv'

# csvファイルの作成 / 文字化け防止にutf-8 / 空行が挟まるのを防ぐ
with open(csv_filename, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f) # 開いたファイルをカンマ区切り(CSV形式)で準備する
    writer.writerow(['URL', 'Title']) # 1行目にURLとTitleという文字を書き込む
    for url, title in site_map.items(): # site_mapに保存したURL、タイトルのペアを順番に全て取り出す
        writer.writerow([url, title]) # site_mapから取り出したURL、タイトルをCSVファイルに1行ずつ書き出す

print(f"CSVファイル '{csv_filename}' への保存が完了しました！")
