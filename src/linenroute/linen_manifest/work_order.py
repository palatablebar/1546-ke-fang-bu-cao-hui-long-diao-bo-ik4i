def collect_stock_cage(measures, missing, estimate):
    on_hand = measures['on_hand']
    if not (on_hand<170):
        return None
    value=on_hand
    return {'现场复核':'确认净件笼','可复查值':round(value,3),'单位':'件','归档要求':'调拨单与干品笼双人点收',
            '需补测':not set(missing).isdisjoint(('on_hand',))}


def collect_truck_ready(measures, missing, estimate):
    truck_eta = measures['truck_eta']
    if not (truck_eta>100):
        return None
    value=truck_eta
    return {'现场复核':'承诺回车','可复查值':round(value,3),'单位':'分钟','归档要求':'核对干衣库与同城车出发时刻',
            '需补测':not set(missing).isdisjoint(('truck_eta',))}


def collect_room_reset(measures, missing, estimate):
    concert_rooms = measures['concert_rooms']
    if not (concert_rooms>=35):
        return None
    value=2*concert_rooms
    return {'现场复核':'团抵换套','可复查值':round(value,3),'单位':'件','归档要求':'锁定团抵前换套笼',
            '需补测':not set(missing).isdisjoint(('concert_rooms',))}


def collect_wash_reject(measures, missing, estimate):
    wash_reject = measures['wash_reject']
    if not (wash_reject>=10):
        return None
    value=wash_reject
    return {'现场复核':'隔离洗涤剔除','可复查值':round(value,3),'单位':'%','归档要求':'分别记录干品和待洗笼',
            '需补测':not set(missing).isdisjoint(('wash_reject',))}


def check_linen_manifest(records):
    guide = []
    for ticket in records:
        if ticket['state'] not in ('已分派','暂停','人工判读'):
            continue
        measures=ticket['measurements']
        absent=ticket['unmeasured']
        estimate=ticket['estimate']
        checks = (
            collect_stock_cage(measures,absent,estimate),
            collect_truck_ready(measures,absent,estimate),
            collect_room_reset(measures,absent,estimate),
            collect_wash_reject(measures,absent,estimate),
        )
        required=tuple(check for check in checks if check is not None)
        if not required:
            continue
        review=ticket['key']
        for check in required:
            guide.append({'签收单':review,'作业区':ticket['zone'],'处置':ticket['state'],**check})
    return guide
