import pandas as pd
df = pd.read_csv("kaiincsv_touroku_Mod20180613.csv", encoding="utf-8")
print(df)

# データフレームを作成
df = pd.DataFrame(
  columns=['id', 'name', 'job'])

# CSV ファイル (employee.csv) として出力
df.to_csv("testcsv_output.csv",encoding="utf-8")
