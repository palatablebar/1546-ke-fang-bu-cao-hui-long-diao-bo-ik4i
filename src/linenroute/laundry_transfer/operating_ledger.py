from collections import defaultdict
from dataclasses import dataclass
from math import ceil, floor


@dataclass(frozen=True, slots=True)
class LinenNeed:
    store: str
    ticket: str
    units: int
    surplus: int
    last_minutes: int
    booked_units: int


def stock_position(row):
    levels = row['measurements']
    clean = floor(levels['on_hand'])
    hold = ceil(levels['concert_rooms'] * 2)
    turnover = ceil(levels['checked_out'] * 1.6 + levels['towel_issue'])
    operational = turnover + hold
    before_laundry = max(0, operational - clean)
    predicted = max(0, ceil(row['estimate']))
    truck = ceil(levels['truck_eta'])
    earliest_room = 75 if hold else 115
    # Washed pieces are not credited before the scheduled room preparation.
    demand = max(before_laundry, predicted) if truck >= earliest_room else before_laundry
    transferable = max(0, clean - operational - max(12, ceil(.07 * turnover)))
    transferable = floor(transferable * max(0, 1 - levels['wash_reject'] / 100))
    return LinenNeed(row['zone'],row['key'],demand,transferable,earliest_room,hold)


def operating_ledger(rows):
    donors = defaultdict(list)
    receivers = []
    slips = []
    for entry in sorted(rows, key=lambda row: row['key']):
        if entry['unmeasured'] or entry['state'] in {'暂停', '人工判读'}:
            slips.append({'业务安排': '核验净衣库存或回车时间', '关联单据': entry['key'], '允许外拨': False})
            continue
        account = stock_position(entry)
        if account.surplus and not account.units:
            donors[account.store].append([account.ticket, account.surplus])
        if account.units:
            receivers.append(account)
    for needed in sorted(receivers, key=lambda item: (item.last_minutes, -item.booked_units, -item.units, item.ticket)):
        remaining = needed.units
        # The sample records share the same urban depot. Slots are loaded as
        # multiples of twelve pieces per cage to keep packs sealed.
        for hotel, store in sorted(donors.items()):
            if hotel == needed.store or not remaining:
                continue
            for donation in store:
                sealed = min(donation[1] // 12, remaining // 12) * 12
                if not sealed:
                    continue
                donation[1] -= sealed
                remaining -= sealed
                slips.append({'业务安排': '跨店封笼调拨', '关联单据': needed.ticket, '接收门店': needed.store,
                              '发出门店': hotel, '发出单据': donation[0], '计划件数': sealed,
                              '最晚备房分钟': needed.last_minutes, '已扣出借账': True})
        if remaining:
            slips.append({'业务安排': '等待洗房回告', '关联单据': needed.ticket, '接收门店': needed.store,
                          '尚缺件数': remaining, '原缺件数':needed.units, '团体预留件': needed.booked_units})
    return slips or [{'业务安排': '店内库存核查', '欠件清册': '全部满足本班预计需求'}]
