#パピモからアイランド秋葉原店の偽物語Aのデータ取得

# imports
import urllib.request, urllib.error
from bs4 import BeautifulSoup
from time import sleep
import datetime
import re
import shutil
import csv

# 取得する台番号List
target_lists = [708,710,711,712,713,715,716,717,718,720]

# アクセスするURL
#base_url = 'https://daidata.goraggio.com/100245/detail?unit='
base_url='https://papimo.jp/h/00031715/hit/view/'

#output_text = '最大持玉,累計スタート,前日最終スタート,合成確率,BB確率,RB確率,'
output_text = '日付,台番号,本日,BB回数,RB回数,BB確率,合成確率,総スタート,最終スタート,最大出メダル,'
now = datetime.datetime.now()
now = now + datetime.timedelta(days=-1)
now = now.strftime('%Y/%m/%d')

for i in target_lists:
	sleep(1)
	#ヘッダ
	#output_text = output_text + '\n'+ now + ',' + str(i) + ','
	# URLにアクセスする htmlが帰ってくる
	url = base_url + str(i)
	html = urllib.request.urlopen(url)
	# htmlをBeautifulSoupで扱う
	soup = BeautifulSoup(html, 'html.parser')
	#店名と機種名を取得する
	hall_name = soup.find('div',{'class':'store-ttl'}).get_text()
	hall_name = '店名：' + hall_name
	machine_name = soup.find('p',{'class':'name'}).get_text()
	machine_name = '機種：' + machine_name
	header_info = hall_name + '\n' + machine_name + '\n'
	#テーブルを指定
	table = soup.findAll('table',{'class':'data'})[0]
	tbody = table.findAll('tbody')[0]
	rows = tbody.findAll('tr')[1]
	#for row in rows:
	for cell in rows.findAll('td'):
		td_text = cell.get_text()
		td_text = td_text.strip()
		td_text = td_text.replace(',','')
		td_text = td_text.replace('1/','')	
		output_text = output_text + td_text + ','

print(output_text)

#CSVの出力
#-*- coding: utf-8 -*-

# ファイルオープン
f = open('output.csv', 'w')

# 出力
#writer.writerow(output_text)
f.write(output_text)

# ファイルクローズ
f.close()

#ファイルをコピーして今日日付のファイルを作る（サマリファイル）
#shutil.copyfile('./zenjitu.csv','toujitu.csv')