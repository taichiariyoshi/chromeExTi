# -*- coding: utf-8 -*-

# 通過データ CSV読み込み 関数
import glob
import json
import math
import matplotlib.pyplot as plt
import os
import os.path
from os import pardir
import pandas as pd
import re
import sys
import urllib.parse
import urllib.request
from IPython.core.display import display, HTML

def read_csv(dir, file):
    log = pd.read_csv(dir + '/' + file,
                  header=None,
                  usecols=[0, 1, 3, 7], #parse only these columns
                  names=['epc', 'time', 'rssi', 'port'], #set columns names
                  ## parse_dates=['c']) #parse datetime
                  dtype={"epc": str, "time": float, "rssi": float, "port": int}
                 ) # 通過時データの読み込み
    log['csv'] = file
    log['time'] = log['time'] - 1511700000.0  # 桁が大きすぎるので一定数引く
    log['epc'] = log['epc'].apply(lambda x: x[-4:])  # 末尾４文字を取り出す
    # 通過したかどうかを算出
    epcs = file.split('.')[1].split('-')
    log['expected'] = log['epc'].apply(lambda x: x in epcs)
    ## log = log.set_index(['csv', 'epc', 'time'])
    # 何秒目か算出
    time_min = log['time'].min()
    log['sec'] = log['time'] - time_min
    import math
    log['sec_bin'] = log['sec'].apply(lambda x: math.floor(x * 2) / 2)
    # 不要な列削除
    del log['time']
    # 列並べ替え
    log = log[['csv', 'epc', 'expected', 'sec', 'sec_bin', 'rssi', 'port']]
    # 商品名付与
    log['product_name'] = get_product_names(log['epc'])
    # 複数EPCが貼られていて、一番反応したEPCじゃないならFalse
    __insert_main_epc(log)
    return log

def read_dir(dir):
    # キャッシュファイルがあればそこから読む
    cache_path = dir + '/.cache'
    if os.path.exists(cache_path):
        log = pd.read_csv(cache_path, dtype={"csv": str, "epc": str, "expected": bool, "sec": float, "sec_bin": float, "rssi": float, "port": int, "product_name": str, "main_epc": bool})
        return log
    # 全CSVのロード
    log = pd.DataFrame()
    for file in glob.glob(dir + '/*.csv'):
        file = file.split('\\')[-1]  # ファイル名だけを取り出す
        log = log.append(read_csv(dir, file))
    log.set_index('csv').to_csv(cache_path, encoding='utf-8')
    return log

def download_dir(directory):
    """
    指定したディレクトリにあるCSVファイルをダウンロードする.
    :param
        directory: {str} CSVをダウンロードするディレクトリ名
    :return
        {DataFrame} CSVファイルの内容をMergeしたもの
    """
    MIN_VALUE, MAX_VALUE = -69.5, -30.0
    CACHE_DIR = 'download/cache'
    CSV_URL = 'http://13.113.187.194:1337/rfid/pass'
    # キャッシュのパス
    current_dir = os.path.abspath(os.path.dirname(__file__))  # スクリプトのディレクトリ
    parent_dir = os.path.abspath(os.path.join(current_dir, pardir))  # スクリプトの親ディレクトリ
    APP_HOME = parent_dir
    CACHE_PATH = APP_HOME + '/' + CACHE_DIR + '/' + directory.replace('/', '--') + '.csv'
    # キャッシュがあればそこから読む
    #if os.path.exists(CACHE_PATH):
        #log = pd.read_csv(CACHE_PATH, dtype={"csv": str, "epc": str, "expected": bool, "sec": float, "sec_bin": float, "rssi": float, "port": int, "product_name": str, "main_epc": bool})
        #return log
    # なければWebから取得
    with urllib.request.urlopen(CSV_URL + '?' + urllib.parse.urlencode({'dir': directory})) as res:
        json_list = res.read().decode("utf-8").split("\n")
    data = []
    for rfid_json in filter(lambda j: j != '', json_list):
        rfid_pass = json.loads(rfid_json)
        before_x = rfid_pass['beforeWidth'] * rfid_pass['oneSecLength']
        for pid, rfid_prod in rfid_pass['products'].items():
            epcs = []
            for epc, rfid_epc in rfid_prod['epcs'].items():
                rfid_epc['epc'] = epc
                epcs.append(rfid_epc)
            epcs = sorted(epcs, key=lambda v: len(v['dots']), reverse=True)
            is1st = True
            for rfid_epc in epcs:
                for dot in rfid_epc['dots']:
                    port, x, y = dot.split(':')
                    x = float(x) / 1000
                    y = float(y) / 1000
                    sec = x / rfid_pass['oneSecLength'] - rfid_pass['beforeWidth']
                    x = (x - before_x) / (1 - before_x)
                    port = int(port)
                    # csv,epc,expected,sec,sec_bin,rssi,product_name,main_epc
                    value = round((y * (MAX_VALUE - MIN_VALUE) + MIN_VALUE) * 2) / 2
                    data.append([
                        rfid_pass['fileName'],
                        rfid_epc['epc'],
                        rfid_prod['expected'],
                        sec,
                        math.floor(sec * 2) / 2,
                        value,
                        port,
                        rfid_prod['name'],
                        is1st,
                        x,
                        value + 70  # rssi をプラス値にする
                    ])
                is1st = False
    log = pd.DataFrame(data,
                       columns='csv,epc,expected,sec,sec_bin,rssi,port,product_name,main_epc,x,posi_rssi'.split(','))
    log.set_index('csv').to_csv(CACHE_PATH, encoding='utf-8')
    return log

def get_product_names(log_epc):
    products = pd.read_csv(os.path.dirname(__file__) + '/data/products.tsv', dtype={"epc": str, "name": str}, delimiter="\t")
    products['epc'] = products.epc.apply(lambda x: x[-4:])  # 末尾４文字を取り出す
    products = products.set_index('epc').to_dict()['name']
    return log_epc.apply(lambda epc: products[epc] if epc in products else epc)

def __insert_main_epc(log_of_one_csv):
    # 商品, EPC ごとの検知数を出す
    by_epc = log_of_one_csv.groupby(['product_name', 'epc']).agg({'rssi': 'count'}).reset_index()
    # 商品ごとの 最大検知数 を出す
    prod2max = by_epc.groupby(['product_name']).agg({'rssi': 'max'}).to_dict()['rssi']
    # EPC ごとにメインかどうかをセットする
    by_epc['main_epc'] = [prod2max[v.product_name] == v.rssi for i, v in by_epc.iterrows()]
    #by_prod = by_prod.sort_values(by=['csv', 'product_name', 'rssi'], ascending=False)
    # EPCごとのmain_epcのマップを作成
    epc2is_main = by_epc[['epc', 'main_epc']].set_index('epc').to_dict()['main_epc']
    # 元データに差し込む
    log_of_one_csv['main_epc'] = log_of_one_csv.epc.apply(lambda epc: epc2is_main[epc])# [prod2max[v.epc] for i, v in by_epc.iterrows()]
    return log_of_one_csv

# targets で渡した通過の DataFrame の sec と rssi を使って散布図を出力する。csv, epc ごとにグラフを分けて出力する
def scatters_rssi(log, targets):
    """
    RSSI の反応を散布図で出す
    """
    fig = plt.figure(figsize=(20, math.ceil(len(targets) / 5) * 2))  # (w, h) inch
    fig.subplots_adjust(hspace=1)
    n = 0
    for csv, prod in zip(targets.csv, targets.product_name):
        n += 1
        df = log.query('csv == @csv and product_name == @prod')
        ax = fig.add_subplot(math.ceil(len(targets) / 5), 5, n)
        ax.scatter(x=df.sec, y=df.rssi, c=df.port, alpha=0.7)
        ax.set_title(re.sub('^.*\\.(.*)\\.csv', '\\1', csv))
        ax.set_xlabel('sec')
        ax.set_ylim(ymin=-70, ymax=-30)
        ax.set_xlim(xmin=0, xmax=6)

def read_usual(path):
    not_log = pd.read_csv(os.path.dirname(__file__) + '/' + path, dtype={"EPC": int, "TIMESTAMP": int, "RSSI": float}) # 非通過時データの読み込み
    not_log.columns = ['epc', 'timestamp', 'rssi']
    not_log['epc'] = not_log['epc'].apply(lambda x: '%04d' % x)
    not_log['timestamp'] = not_log['timestamp'] - 1505095448  # 桁が大きすぎるので一定数引く
    return not_log


class JudgeContext:
    """
    判定ロジックを扱いやすくするめのクラス。
    使用例:
    def 前後のパワー比較2(context, 傾き, 切片):
        work = context.open_work('前後のパワー比較')
        work['前半'] = context.agg(agg='sum', fillna=0, query='port != 100 and 0 <= x < 0.5')
        work['後半'] = context.agg(agg='sum', fillna=0, query='port != 100 and 0.5 <= x')
        return context.close_work(f"後半 - {傾き} * 前半 - {切片} > 0")
    """
    def __init__(self, csv, is_detail=False):
        self.csv = csv
        self.is_detail = is_detail
        self.empty_epcs = csv.pivot_table(index=['epc'])[[]]  # epc が index だけの df を作る
        self.title = None
        self.detail = self.empty_epcs.copy()
        self.detail['log'] = ''
    def open_work(self, title):
        self.title = title
        self.work = self.empty_epcs.copy()
        return self.work
    def agg(self, query=None, agg='count', fillna=0):
        if query == None:
            csv = self.csv
        else:
            csv = self.csv.query(query)
        epcs = csv.groupby('epc')[['posi_rssi']].agg(agg)['posi_rssi']
        epcs = self.empty_epcs.join(epcs) # epc が欠けないように
        epcs = epcs.fillna(fillna)
        return epcs
    def close_work(self, expr):
        # 仮に res にスカラーが渡されてもブロードキャストされるように
        self.work['res'] = self.work.eval(expr)
        res = self.work['res']
        # log整形
        if self.is_detail:
            def _replace_log(log, v_list):
                for i, v in v_list.iteritems():
                    log = log.replace(i, '{}({})'.format(i, v))
                return log
            self.detail['log'] = self.detail['log'] + [f"<{res[i]}> {_replace_log(expr, v)} … 【{self.title}】\n" for i, v in self.work.iterrows()]
        self.work = None
        return res
    def judge(self, judge):
        self.detail['result'] = judge(self)
    def get_results(self):
        return self.detail


def judge_all_data(csvs, judge):
    """
    全CSVデータ
    :param csvs: 全検知データ入りのDataFrame
    :param judge: 判定ロジックの関数
    :return: 結果の入ったDataFrame
    """
    results = pd.DataFrame(columns=['csv', 'epc']).set_index(['csv', 'epc'])

    for name, csv in csvs.groupby('csv'):
        context = JudgeContext(csv, is_detail=True)
        context.judge(judge)
        detail = context.get_results()

        detail['csv'] = name
        detail = detail.reset_index().set_index(['csv', 'epc'])
        results = results.append(detail)

    exp_prod = csvs.groupby(['csv', 'epc']).agg({'expected': 'last', 'product_name': 'last'})
    results = results.join(exp_prod)
    results['godoku'] = (results['expected'] == False) & (results['result'] == True)
    results['midoku'] = (results['expected'] == True) & (results['result'] == False)

    return results


def make_expected_epcs(csvs):
    """
    通過したはずのEPCが入ったDataFrameを返す
    :param csvs:
    :return:
    """
    epc5_to_full = csvs[['epc']].drop_duplicates()
    epc5_to_full['epc5'] = epc5_to_full.epc.apply(lambda epc: re.sub(r'^0x(\d).*(\d{4})$', r'\1\2', epc))
    epc5_to_full = epc5_to_full.set_index('epc5').epc.to_dict()
    #return epc5_to_full

    csv_epc = []
    for csv in csvs[['csv']].drop_duplicates().csv:
        for epc5 in re.sub(r'^.+?\.([\d-]+).*$', r'\1', csv).split('-'):
            if epc5 in epc5_to_full:
                epc = epc5_to_full[epc5]
            else:
                epc = epc5
            csv_epc.append({'csv': csv, 'epc': epc})
    return pd.DataFrame(csv_epc).set_index(['csv', 'epc'])


def count_godoku_midoku(results, expected_list, title):
    by_csv = results.groupby('csv').agg({'midoku':'any', 'godoku':'any'})
    d = {}
    by_prod_ex = results[results.expected == True ].groupby(['csv', 'epc']).agg({'midoku':'any'})
    by_prod_ex = expected_list.join(by_prod_ex).fillna(True)
    by_prod_un = results[results.expected == False].groupby(['csv', 'epc']).agg({'godoku':'any'})
    d['title']              = title
    d['総数(通過)']         = len(by_csv)
    d['未読数(通過)']       = len(by_csv[by_csv.midoku])
    d['誤読数(通過)']       = len(by_csv[by_csv.godoku])
    d['総数(通過商品)']     = len(by_prod_ex)
    d['未読数(通過商品)']   = len(by_prod_ex[by_prod_ex.midoku])
    d['総数(非通過商品)']   = len(by_prod_un)
    d['誤読数(非通過商品)'] = len(by_prod_un[by_prod_un.godoku])
    df = pd.DataFrame([d])
    df['未読率(通過)'] = df['未読数(通過)'] / df['総数(通過)']
    df['誤読率(通過)'] = df['誤読数(通過)'] / df['総数(通過)']
    df['未読率(通過商品)'] = df['未読数(通過商品)'] / df['総数(通過商品)']
    df['誤読率(非通過商品)'] = df['誤読数(非通過商品)'] / df['総数(通過)']
    return df

def print_midoku_godoku(df, graph=True):
    if graph:
        df[['未読率(通過)', '誤読率(通過)', '未読率(通過商品)', '誤読率(非通過商品)']].plot()
        plt.show()

    def _percent(分子, 分母, 単位):
        return f"{分子 / 分母:.1%} ({int(分子):>2} / {int(分母):>4}{単位})"
    for title, v in df.iterrows():
        text = ''
        text += f"通過ごと： "
        text += f"誤読 {_percent(v['誤読数(通過)'], v['総数(通過)'], '回')}  "
        text += f"未読 {_percent(v['未読数(通過)'], v['総数(通過)'], '回')}        "
        text += f"商品ごと： "
        text += f"誤読 {_percent(v['誤読数(非通過商品)'], v['総数(非通過商品)'], '個')}  "
        text += f"未読 {_percent(v['未読数(通過商品)'], v['総数(通過商品)'], '個')}"
        print(text)

def assert_pd(actual, expected, message=''):
    if isinstance(actual, (pd.DataFrame, pd.Series)):
        actual = json.dumps(actual.T.to_dict(), ensure_ascii=False)
    if type(expected) != str and type(expected) != bool:
        expected = json.dumps(expected, ensure_ascii=False)
    if actual != expected:
        raise Exception(f"Assert Error!! {message}\nactual:   {actual}\nexpected: {expected}\n")


def graph_all(csvs, results, directory):

    def show_link(csv, title):
        display(HTML(f"""<a href="http://13.113.187.194:1337/epc_test/{csv}?dir={directory}">{title}</a>"""))

    def scatters_rssi(log, targets, title):
        """
        RSSI の反応を散布図で出す
        """
        fig = plt.figure(figsize=(20, math.ceil(len(targets) / 5) * 2))  # (w, h) inch
        fig.subplots_adjust(hspace=1)
        fig.suptitle(title, fontsize=20)
        n = 0
        for csv, prod in zip(targets.csv, targets.product_name):
            n += 1
            df = log.query('csv == @csv and product_name == @prod')
            ax = fig.add_subplot(math.ceil(len(targets) / 5), 5, n)
            ax.scatter(x=df.sec, y=df.rssi, c=df.port, alpha=0.7)
            ax_title = re.sub(r'^.*\.(.*)_\d*-\d*-\d*\.csv', r'\1', csv)
            ax.set_title(ax_title)
            ax.set_xlabel('sec')
            ax.set_ylim(ymin=-70, ymax=-30)
            #ax.set_xlim(xmin=0, xmax=6)
            show_link(csv, f"{title} {prod} {ax_title}")

    def get_percent(values):
        """
        DataFrame にパーセンテージを追加するための関数
        """
        sum = values.sum()
        return values / sum * 100

    # pie_graph(results, "godoku")
    # pie_graph(results, "midoku")
    def pie_graph(results, go_or_mi):
        desc = results.query(f"{go_or_mi} == True").groupby('product_name')[go_or_mi]
        if len(desc) == 0:
            return

        desc = desc.describe()
        desc['percent'] = get_percent(desc['count'])

        # グラフ
        desc['percent'].sort_values(ascending=False).plot.pie(counterclock=False, startangle=90, autopct='%1.1f%%')
        plt.axis('equal')  # 楕円にしない
        plt.ylabel('')
        plt.title(go_or_mi)
        plt.show()


    def scatters_rssi_all(csvs, results, go_or_mi, product_top=4):
        products = results.query(go_or_mi + " == True").groupby('product_name')[[go_or_mi]]
        if len(products) == 0:
            return
        products = products.count().nlargest(product_top, go_or_mi).index
        for prod in products:
            scatters_rssi(csvs, results.reset_index().query(go_or_mi + ' == True and product_name == @prod'), go_or_mi + ' ' + prod)

    pie_graph(results, "godoku")
    pie_graph(results, "midoku")

    scatters_rssi_all(csvs, results, "godoku", product_top=4)
    scatters_rssi_all(csvs, results, "midoku", product_top=4)
