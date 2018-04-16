# imports
import urllib.request, urllib.error
from bs4 import BeautifulSoup
from time import sleep
import datetime

# 取得する台番号List
#target_lists = [226,228,229,230,231,232,233,234,235,236,237,238,239,240,241,242]
target_lists = [156,157,158,159]

# アクセスするURL
#base_url = "https://daidata.goraggio.com/100245/detail?unit="
base_url="https://daidata.goraggio.com/100227/detail?unit="

output_text = "最大持玉,累計スタート,前日最終スタート,合成確率,BB確率,RB確率,"
now = datetime.datetime.now()
now = now.strftime("%Y/%m/%d")

for i in target_lists:
	sleep(1)
	output_text = output_text + "\n"+ now + "," + str(i) + ","
	# URLにアクセスする htmlが帰ってくる
	url = base_url + str(i)
	html = urllib.request.urlopen(url)
	# htmlをBeautifulSoupで扱う
	soup = BeautifulSoup(html, "html.parser")
	#テーブルを指定
	table = soup.findAll("table",{"class":"overviewTable3"})[0]
	rows = table.findAll("tr")
	for row in rows:
		for cell in row.findAll('td'):
			td_text = cell.get_text()
			td_text = td_text.strip()
			output_text = output_text + td_text + ","

print (output_text)



