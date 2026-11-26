from dataclasses import dataclass
from math import sqrt, fsum
from statistics import median


@dataclass(frozen=True, slots=True)
class DomainStudy:
    counts: tuple[int, int, int]
    rate: float | None
    midpoint: float | None
    expected: float | None
    drift: float | None

def occupancy_shift_domains(vectors):
    minimum_reset = []
    clean_margin = []
    shortage_risk = []
    margin_minutes = []
    cart_utility = []
    resupply_cost = []
    wash_discard = []
    block_cover = []
    for measurement in vectors:
        unobserved = frozenset(measurement.missing)
        checked_out, on_hand, truck_eta, towel_issue, wash_reject, concert_rooms = measurement.input_values
        if unobserved.isdisjoint(('checked_out', 'concert_rooms')):
            minimum_reset.append((round(2*checked_out, 4), concert_rooms>=56))
        if unobserved.isdisjoint(('checked_out', 'on_hand', 'truck_eta', 'towel_issue')):
            clean_margin.append((round(on_hand-2*checked_out-towel_issue, 4), truck_eta>=140))
        if unobserved.isdisjoint(('checked_out', 'on_hand', 'towel_issue', 'concert_rooms')):
            shortage_risk.append((round(max(0,2*checked_out+towel_issue+2*concert_rooms-on_hand), 4), on_hand<130))
        if unobserved.isdisjoint(('checked_out', 'truck_eta')):
            margin_minutes.append((round(240-truck_eta, 4), checked_out>=110))
        if unobserved.isdisjoint(('on_hand', 'wash_reject')):
            cart_utility.append((round(on_hand*(1-wash_reject/100)/2, 4), wash_reject>=16))
        if unobserved.isdisjoint(('checked_out', 'towel_issue', 'concert_rooms')):
            resupply_cost.append((round(towel_issue/(1+checked_out), 4), concert_rooms>=56))
        if unobserved.isdisjoint(('checked_out', 'on_hand', 'truck_eta', 'wash_reject')):
            wash_discard.append((round((on_hand+2*checked_out)*wash_reject/100, 4), truck_eta>=140))
        if unobserved.isdisjoint(('on_hand', 'concert_rooms')):
            block_cover.append((round(concert_rooms*2, 4), on_hand<130))
    return {
        '退房最低换套件 · 团体集中到店': tuple(minimum_reset),
        '基础布草减发后库存 · 洗涤迟车': tuple(clean_margin),
        '到店前未覆盖份数 · 净布草低库存': tuple(shortage_risk),
        '距四小时洗回 · 退房量大': tuple(margin_minutes),
        '当前库存可开套数 · 高剔除率': tuple(cart_utility),
        '每间库存周转需求 · 团体集中到店': tuple(resupply_cost),
        '近似剔除件数 · 洗涤迟车': tuple(wash_discard),
        '团抵所需净布草 · 净布草低库存': tuple(block_cover),
    }


def evaluate_domains(training, current):
    references = occupancy_shift_domains(training)
    activity = occupancy_shift_domains(current)
    diagnostics = []
    for domain, observed in activity.items():
        baseline = references.get(domain, ())
        study = characterize(baseline, observed)
        diagnostics.append({'观察维度': domain, '训练有效量': study.counts[0], '当班有效量': study.counts[1],
                            '越线量':study.counts[2], '越线比例':study.rate, '参考中位':study.midpoint,
                            '当班中位':study.expected, '相对训练变化':study.drift})
    return diagnostics


def characterize(before, after):
    history = tuple(value for value, _ in before)
    observed = tuple(value for value, _ in after)
    violating = sum(flag for _, flag in after)
    old = median(history) if history else None
    new = median(observed) if observed else None
    pct = round(violating / len(after), 4) if after else None
    movement = round(new - old, 4) if old is not None and new is not None else None
    return DomainStudy((len(before),len(after),violating),pct,old,new,movement)
