import pandas as pd
import TestCsv

def 前後のパワー比較(csv, epc2res, epc2log, 傾き, 切片):
    """
    通過したEPCを特定し、返却します.
    """
    csv = csv.query('x >= 0').copy()

    # [csv, epc, sec_part(1 or 2), rssi]
    csv['sec_part'] = [1 if (x < 0.5) else 2 for x in csv.x]  # 前半か後半か

    by_sec = csv.groupby(['epc', 'sec_part']).agg({'posi_rssi': 'sum'}).rename(columns={'posi_rssi': 'power'})
    by_epc = by_sec.pivot_table(index=['epc'], columns=['sec_part'], values=['power']).fillna(0)
    by_epc.columns = ['power1', 'power2']

    # 後半のPower - (分離超平面の傾き * 前半のPower + 分離超平面の切片) = どれだけ正読であるのか. 値がプラスである程正読.
    by_epc['judging'] = by_epc['power2'] - (傾き * by_epc['power1'] + 切片)
    by_epc['res'] = by_epc['judging'] > 0
    by_epc['log'] = [
        f"<{0 < j}> res({j}) = power2({p2}) - {傾き * p1 + 切片}( {傾き} * power1({p1}) + {切片} )"
        for j, p1, p2 in zip(by_epc['judging'], by_epc['power1'], by_epc['power2'])
    ]
    epc2res = epc2res.merge(by_epc[['res', 'power1', 'power2']].rename(columns={'res': '前後のパワー比較'}), how='outer',
                            left_index=True, right_index=True).fillna(False)
    epc2log = epc2log.merge(by_epc[['log']].rename(columns={'log': '前後のパワー比較'}), how='outer', left_index=True,
                            right_index=True).fillna("")

    return epc2res, epc2log


def 一定以上の検知数のみ通過(csv, epc2res, epc2log, 最小検知回数):
    """
    後半の検知回数が少ないEPCを除外する.
    """
    # TODO (junki.kato)Modelファイル(YAMLとかで記述)から取得する様に変更
    func_name = 一定以上の検知数のみ通過.__name__

    result = csv.query('x >= 0.5').groupby(['epc']).agg({'sec': 'count'}).rename(columns={'sec': 'count'})
    result['result'] = result['count'] > 最小検知回数
    result['reason'] = [
        f"<True> 最小検知回数({最小検知回数}) ＜ 検知数({v['count']})" if v['count'] > 最小検知回数 else f"<False> 検知数({v['count']}) ≦ 最小検知回数({最小検知回数})" for
        i, v in result.iterrows()]

    epc2res = epc2res.merge(result[['result']].rename(columns={'result': func_name}), how='outer', left_index=True,
                            right_index=True).fillna(False)
    epc2log = epc2log.merge(result[['reason']].rename(columns={'reason': func_name}), how='outer', left_index=True,
                            right_index=True).fillna(False)

    return epc2res, epc2log


def 電波強度のバラ付きが大きい場合は通過(csv, epc2res, epc2log, 平均からの距離):
    """
    全体的に一定の強さ(平均値から1割以内)に収まる場合、非通過と判定.
    """
    func_name = 電波強度のバラ付きが大きい場合は通過.__name__

    means_by_epc = csv.query('x >= 0').groupby(['epc']).agg({'posi_rssi': 'mean'}).rename(columns={'posi_rssi': 'mean'})
    csv = pd.merge(csv.reset_index(), means_by_epc.reset_index(), on='epc')
    csv['overflow_for_sum'] = [
        1 if (v['posi_rssi'] < v['mean'] * (1 - 平均からの距離)) or (v['mean'] * (1 + 平均からの距離) < v['posi_rssi']) else 0 for
        i, v in
        csv.iterrows()]
    csv = csv[['epc', 'rssi', 'mean', 'overflow_for_sum']]
    csv = csv.groupby('epc').agg({'rssi': 'count', 'overflow_for_sum': 'sum'}).rename(
        columns={'rssi': 'detected_count', 'overflow_for_sum': 'overflow_count'})
    csv['result'] = [v['detected_count'] * 0.1 <= v['overflow_count'] for i, v in csv.iterrows()]
    epc2res = epc2res.merge(csv[['result']].rename(columns={'result': func_name}), how='outer', left_index=True,
                            right_index=True).fillna(False)
    csv[func_name] = [f"<{v['result']}> RSSI平均値 ±{平均からの距離 * 100}%越え : {v['overflow_count'] / v['detected_count'] * 100}%" for i, v in csv.iterrows()]
    epc2log = epc2log.merge(csv[[func_name]], how='outer', left_index=True, right_index=True).fillna(False)

    return epc2res, epc2log


def 通過前の検知数が通過時より多い場合は除外(csv, epc2res, epc2log, 倍率):
    """
    ゲート進入前の検知回数 > 通過時の検知件数 の場合、非通過と判定する.
    """
    func_name = 通過前の検知数が通過時より多い場合は除外.__name__

    通過前 = csv.query('x <= 0').groupby('epc').count()[['rssi']].rename(columns={'rssi': '検知数_通過前'})
    通過中 = csv.query('0 < x').groupby('epc').count()[['rssi']].rename(columns={'rssi': '検知数_通過中'})

    merged = 通過前.merge(通過中, how='outer', left_index=True, right_index=True).fillna(False)
    merged['result'] = [v['検知数_通過前'] * 倍率 < v['検知数_通過中'] for i, v in merged.iterrows()]
    merged['reason'] = [f'<True> 通過前×{倍率}({int(v["検知数_通過前"]) * 倍率}) < 通過({int(v["検知数_通過中"])})' if v[
        'result'] else f'<False> 通過前×{倍率}({int(v["検知数_通過前"]) * 倍率}) ≧ 通過({v["検知数_通過中"]})' for i, v in merged.iterrows()]

    epc2res = epc2res.merge(merged[['result']].rename(columns={'result': func_name}), how='outer', left_index=True, right_index=True).fillna(False)
    epc2log = epc2log.merge(merged[['reason']].rename(columns={'reason': func_name}), how='outer', left_index=True, right_index=True).fillna(False)

    return epc2res, epc2log


def 通過時のRSSI最大値が閾値を下回るものは除外(csv, epc2res, epc2log, RSSI最大値, 上回る回数):
    """
    通過時のRSSI最大値が閾値を下回るものは除外.
    """
    func_name = 通過時のRSSI最大値が閾値を下回るものは除外.__name__

    最大値リスト = csv.groupby('epc').agg({'rssi': 'max'}).rename(columns={'rssi': 'max'})
    閾値超え = csv.query('rssi > @RSSI最大値 and x > 0.5').groupby('epc').count()[['rssi']].rename(columns={'rssi': '閾値超え'})
    閾値超え = 閾値超え.merge(最大値リスト, how='outer', left_index=True, right_index=True).fillna(False)

    merged = epc2res.merge(閾値超え, how='outer', left_index=True, right_index=True).fillna(False)
    merged['result'] = [v['閾値超え'] > 上回る回数 for i, v in merged.iterrows()]
    merged['reason'] = [f"<True> RSSI閾値({RSSI最大値})越え({v['閾値超え']}回) ＞ 0" if v[
        'result'] else f"<False> 0 ≦ RSSI閾値({RSSI最大値})越え({v['閾値超え']}回) : RSSI最大値({v['max']})" for i, v in
                        merged.iterrows()]

    epc2res = epc2res.merge(merged[['result']].rename(columns={'result': func_name}), how='outer', left_index=True,
                            right_index=True).fillna(False)
    epc2log = epc2log.merge(merged[['reason']].rename(columns={'reason': func_name}), how='outer', left_index=True,
                            right_index=True).fillna(False)

    return epc2res, epc2log

def プラレール(csv, epc2res, epc2log):
    """
    プラレールは除外.
    """
    func_name = プラレール.__name__

    by_epc = csv.pivot_table(index='epc')[[]]
    by_epc['result'] = [epc4[-4] != '4' for epc4 in by_epc.index]

    epc2res = epc2res.merge(by_epc[['result']].rename(columns={'result': func_name}), how='outer', left_index=True, right_index=True).fillna(False)

    return epc2res, epc2log


def judge_all_data(csvs, プラレール除外=False):
    def _main(csv, epc2res, epc2log):
        epc2res, epc2log = 通過前の検知数が通過時より多い場合は除外(csv, epc2res, epc2log, 倍率=2.0)
        epc2res, epc2log = 通過時のRSSI最大値が閾値を下回るものは除外(csv, epc2res, epc2log, RSSI最大値=-58, 上回る回数=2)
        epc2res, epc2log = 一定以上の検知数のみ通過(csv, epc2res, epc2log, 最小検知回数=2)
        epc2res, epc2log = 電波強度のバラ付きが大きい場合は通過(csv, epc2res, epc2log, 平均からの距離=0.1)
        epc2res, epc2log = 前後のパワー比較(csv, epc2res, epc2log, 傾き=0.7, 切片=58)
        if プラレール除外 == True:
            epc2res, epc2log = プラレール(csv, epc2res, epc2log)
        return epc2res, epc2log
    def _after(results):
        #return results['通過前の検知数が通過時より多い場合は除外'] & results['一定以上の検知数のみ通過'] & results['電波強度のバラ付きが大きい場合は通過'] & results['前後のパワー比較'] & results['通過時のRSSI最大値が閾値を下回るものは除外'] & results['プラレール']
        res = (
                results['通過前の検知数が通過時より多い場合は除外']
                & results['一定以上の検知数のみ通過']
                & results['電波強度のバラ付きが大きい場合は通過']
                & results['前後のパワー比較']
                & results['通過時のRSSI最大値が閾値を下回るものは除外']
        )
        if プラレール除外 == True:
            res = res & results['プラレール']
        return res

    results = pd.DataFrame(columns=['csv', 'epc', 'product_name', 'expected']).set_index(['csv', 'epc'])

    for name, csv in csvs.groupby('csv'):
        # 引数の準備
        epc2res = csv.pivot_table(index=['epc'])[[]]  # epc が index だけの df を作る
        epc2log = epc2res.copy(deep=True)

        # 判定
        epc2res, epc2log = _main(csv, epc2res, epc2log)

        epc2res['csv'] = name
        epc2res = epc2res.reset_index().set_index(['csv', 'epc'])

        # 付加情報を見る
        exp_prod = csv.groupby(['csv', 'epc']).agg({'expected': 'last', 'product_name': 'last'})
        merged = pd.concat([epc2res, exp_prod], axis=1)

        results = results.append(merged)

    results['result'] = _after(results)
    #results = [(v['一定以上の検知数のみ通過'] and v['前後のパワー比較']) for i, v in epc2res.iterrows()]
    #results['result'] = results['前後のパワー比較']
    #results['result'] = results['電波強度のバラ付きが大きい場合は通過'] & results['前後のパワー比較']
    #results['result'] = results['電波強度のバラ付きが大きい場合は通過']
    results['godoku'] = (results['expected'] == False) & (results['result'] == True)
    results['midoku'] = (results['expected'] == True) & (results['result'] == False)

    return results

