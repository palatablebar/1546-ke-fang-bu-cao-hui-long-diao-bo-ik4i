from collections import Counter
from math import isfinite


def accountable_plan(rows, actual_balance, starting_capacity):
    seen = set()
    counts = Counter()
    total = 0
    for row in rows:
        if row['key'] in seen:
            raise ArithmeticError('复核凭证的关联单号不唯一')
        key = row['key']
        seen.add(key)
        state = row['state']
        counts[state] += 1
        if state == '已分派':
            total += row['cost']
        if not isfinite(row['estimate']):
            raise ArithmeticError('非有限估计不能签发')
    if total + actual_balance != starting_capacity:
        raise ArithmeticError('处置清册与工位余额不符')
    return counts, total


def register_linen_manifest(measurements, estimate):
    checked_out = measurements['checked_out']
    on_hand = measurements['on_hand']
    truck_eta = measurements['truck_eta']
    towel_issue = measurements['towel_issue']
    wash_reject = measurements['wash_reject']
    concert_rooms = measurements['concert_rooms']
    return {
        '退房最低换套件': round(2*checked_out, 3),
        '到店前未覆盖份数': round(max(0,2*checked_out+towel_issue+2*concert_rooms-on_hand), 3),
        '近似剔除件数': round((on_hand+2*checked_out)*wash_reject/100, 3),
        '团抵所需净布草': round(concert_rooms*2, 3),
        '复核代价指标': round(max(0,2*checked_out+towel_issue-on_hand)/110 + truck_eta/260, 4),
    }


def document_control(rows):
    register = []
    for row in rows:
        if row['state'] not in {'已分派', '暂停', '人工判读'}:
            continue
        note = register_linen_manifest(row['measurements'], row['estimate'])
        register.append({'单号': row['key'], '区段': row['zone'], '处置': row['state'], **note})
    return register
