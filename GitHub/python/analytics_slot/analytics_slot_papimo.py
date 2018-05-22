#パピモからアイランド秋葉原店の花火のデータ取得

# imports
import urllib.request, urllib.error
from bs4 import BeautifulSoup
from time import sleep
import datetime
import re

# 取得する台番号List
#target_lists = [226,228,229,230,231,232,233,234,235,236,237,238,239,240,241,242]
target_lists = [702,703,705,706,707]

# アクセスするURL
#base_url = 'https://daidata.goraggio.com/100245/detail?unit='
base_url='https://papimo.jp/h/00031715/hit/view/'

#output_text = '最大持玉,累計スタート,前日最終スタート,合成確率,BB確率,RB確率,'
output_text = '日付,台番号,本日,BB回数,RB回数,BB確率,合成確率,総スタート,最終スタート,最大出メダル,'
now = datetime.datetime.now()
now = now.strftime('%Y/%m/%d')

for i in target_lists:
	sleep(1)
	output_text = output_text + '\n'+ now + ',' + str(i) + ','
	# URLにアクセスする htmlが帰ってくる
	url = base_url + str(i)
	html = urllib.request.urlopen(url)
	# htmlをBeautifulSoupで扱う
	soup = BeautifulSoup(html, 'html.parser')
	#店の名前と機種名を取得する
	hall_name = soup.find('div',{'class':'store-ttl'}).get_text()
	hall_name = '店名：' + hall_name
	machine_name = soup.find('p',{'class':'name'}).get_text()
	machine_name = '機種：' + machine_name
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

print(hall_name)
print(machine_name)
print (output_text)

#CSVの出力
# -*- coding: utf-8 -*-

import csv

# ファイルオープン
f = open('output.csv', 'w')

#writer = csv.writer(f, lineterminator='\r\n')

# データをリストに保持
#csvlist = []
#csvlist.append(output_text)

# 出力
#writer.writerow(output_text)
f.write(output_text)

# ファイルクローズ
f.close()

