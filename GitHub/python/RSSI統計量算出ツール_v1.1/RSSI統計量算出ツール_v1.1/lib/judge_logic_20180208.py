"""
通過時のデータを基に、通過したEPCを特定するロジック群.
"""

import pandas as pd


def 前後のパワー比較(context, 傾き, 切片):
    """
    通過したEPCを特定し、返却します.
    :param
        傾き: 分離超平面の傾き
        切片: 分離超平面の切片
    :return
        {DataFrame} EPC毎の判定結果と判定理由
    """
    work = context.open_work('前後のパワー比較')
    work['前半'] = context.agg(agg='sum', fillna=0, query='port != 100 and 0 <= x < 0.5')
    work['後半'] = context.agg(agg='sum', fillna=0, query='port != 100 and 0.5 <= x')
    return context.close_work(f"後半 - {傾き} * 前半 - {切片} > 0")


def 一定以上の検知数のみ通過(context, 最小検知回数):
    """
    後半の検知回数が少ないEPCを除外する.
    :param
        最小検知回数: {int} 検知回数の閾値(この検知回数を下回ると、非通過と判定する)
    :return
        {DataFrame} EPC毎の判定結果と判定理由
    """
    work = context.open_work('一定以上の検知数のみ通過')
    work['後半検知数'] = context.agg(agg='count', fillna=0, query='port != 100 and 0.5 <= x')
    return context.close_work(f"{最小検知回数} < 後半検知数")


def 電波強度のバラ付きが大きい場合は通過(context, 平均からの距離, はみ出た割合):
    """
    平均値から一定の範囲を越えるRSSIを検知した回数が、閾値を越えないEPCは、非通過と判定する.
    :param
        平均からの距離: {float} 一定の強さと言える範囲の割合
        はみ出た割合: {float} はみ出た検知回数が、この割合を下回ると非通過
    :return
        {DataFrame} EPC毎の判定結果と判定理由
    """
    work = context.open_work('電波強度のバラ付きが大きい場合は通過')
    work['検知回数'] = context.agg(agg='count', fillna=0)

    def __(df):
        rssi = df.posi_rssi
        mean = rssi.mean()
        return len(df[abs(rssi - mean) > mean * 平均からの距離])

    work['はみ出た数'] = context.agg(agg=__, fillna=0)
    return context.close_work(f"はみ出た数 > 検知回数 * {はみ出た割合}")


def 通過前の検知数が通過時より多い場合は除外(context, 倍率):
    """
    ゲート進入前の検知回数 > 通過時の検知件数 の場合、非通過と判定する.
    :param
        倍率: {float} 通過中の検知数が、通過前の検知数×倍率に満たない場合、非通過と判定する
    :return
        {DataFrame} EPC毎の判定結果と判定理由
    """
    work = context.open_work('通過前の検知数が通過時より多い場合は除外')
    work['通過前'] = context.agg(agg='count', fillna=0, query='port != 100 and x < 0')
    work['通過中'] = context.agg(agg='count', fillna=0, query='port != 100 and 0 <= x')
    return context.close_work(f"通過前 * {倍率} < 通過中")


def 通過時のRSSI最大値が閾値を下回るものは除外(context, RSSI閾値, 回数閾値):
    """
    通過時に、閾値を上回るRSSIを、指定回数以上検知しなかったEPCは、非通過と判定する.
    :param
        RSSI閾値: {float} 通過中のRSSIが閾値に達しない場合、非通過と判定する
        回数閾値: {int} 通過中に閾値を上回るRSSIを回数閾値以上検知出来ない場合、非通過と判定する
    :return
        {DataFrame} EPC毎の判定結果と判定理由
    """
    work = context.open_work('通過時のRSSI最大値が閾値を下回るものは除外')
    work['上回った回数'] = context.agg(agg='count', fillna=0, query=f"port != 100 and 0.5 < x and {RSSI閾値} < rssi")
    return context.close_work(f"{回数閾値} < 上回った回数")


def 磁界型アンテナで検知したら通過(context):
    """
    磁界型アンテナで、一度でも検知したものは通過と判定する.
    :return
        {DataFrame} EPC毎の判定結果と判定理由
    """
    work = context.open_work('磁界型アンテナで検知したら通過')
    work['磁界型アンテナで検知'] = context.agg(agg='count', fillna=0, query=f"port in [5, 6, 7, 8]")
    return context.close_work(f"磁界型アンテナで検知 > 0")


def アンテナ前通過時に100番ポートで検知したら除外(context, 新RWの検知範囲外):
    """
    アンテナ前通過中に、入口付近しか読まないR/Wで検知したEPCは、除外対象とする.
    :param
        新RWの検知範囲外: {float} レーンの何割を通過した所から、100番ポートで検知出来なくなるか(0 < 新RWの検知範囲外 < 1.0)
    :return
        {DataFrame} EPC毎の判定結果と判定理由
    """
    work = context.open_work('アンテナ前通過時に100番ポートで検知したら除外')
    work['ポート100番で検知'] = context.agg(agg='count', fillna=0, query=f"x > {新RWの検知範囲外} and port == 100")
    return context.close_work(f"ポート100番で検知 == 0")


def read_csv(directory, file, start):
    csv = pd.read_csv(directory + '/' + file,
                      header=None,
                      usecols=[0, 1, 3, 7, 10],  # parse only these columns
                      names=['epc', 'time', 'rssi', 'port', 'mode'],  # set columns names
                      ## parse_dates=['c']) #parse datetime
                      dtype={"epc": str, "time": float, "rssi": float, "port": int, "mode": str}
                      )  # 通過時データの読み込み
    # 何秒目か算出
    # csv['time'] = csv['time'] - 1511700000.0  # 桁が大きすぎるので一定数引く
    csv['sec'] = csv['time'] - start
    # 秒の割合
    csv['x'] = csv['sec'] / csv['sec'].max()
    # プラスの RSSI
    csv['posi_rssi'] = csv['rssi'] + 70  # rssi をプラス値にする
    # 列並べ替え
    return csv[['epc', 'sec', 'x', 'rssi', 'posi_rssi', 'port', 'mode']]
