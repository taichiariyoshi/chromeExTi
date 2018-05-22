from selenium import webdriver # さっきpip install seleniumで入れたseleniumのwebdriverというやつを使う

driver = webdriver.Chrome("./chromedriver.exe") # さっきDLしたchromedriver.exeを使う
driver.get("http://www.yahoo.co.jp/") #chrome起動してyahooに移動
searchBox = driver.find_element_by_css_selector("#srchtxt") #検索入力ボックスのhtmlを探す
searchBox.send_keys("世の中 憎い") #その検索ボックスで　「世の中 憎い」と打つ
kensakuBotan = driver.find_element_by_css_selector("#srchbtn") #htmlから検索ボタンを探す
kensakuBotan.click() #検索ボタンをクリック
