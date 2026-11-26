from dataclasses import replace
from statistics import median

from .contracts import TurnoverFactors, Proposal


def measure_turnover_factors(values) -> TurnoverFactors:
    checked_out, on_hand, truck_eta, towel_issue, wash_reject, concert_rooms = values
    return TurnoverFactors(
        minimum_reset=2*checked_out,
        clean_margin=on_hand-2*checked_out-towel_issue,
        shortage_risk=max(0,2*checked_out+towel_issue+2*concert_rooms-on_hand),
        margin_minutes=240-truck_eta,
        cart_utility=on_hand*(1-wash_reject/100)/2,
        resupply_cost=towel_issue/(1+checked_out),
        wash_discard=(on_hand+2*checked_out)*wash_reject/100,
        block_cover=concert_rooms*2,
    )


def propose_laundry_transfer(values, missing=()):
    checked_out, on_hand, truck_eta, towel_issue, wash_reject, concert_rooms = values
    if 'on_hand' not in missing and (on_hand<=440):
        yield Proposal('同城车调入四十件', 'on_hand', on_hand, min(480,on_hand+40), 2)
    if 'truck_eta' not in missing and (truck_eta>=45):
        yield Proposal('急回车提前三十分钟', 'truck_eta', truck_eta, max(15,truck_eta-30), 3)
    if 'concert_rooms' not in missing and (concert_rooms>=22):
        yield Proposal('团抵分两批换套', 'concert_rooms', concert_rooms, max(0,concert_rooms-20), 1)
    if 'wash_reject' not in missing and (wash_reject>=4):
        yield Proposal('分拣复核挽回可用布草', 'wash_reject', wash_reject, max(0,wash_reject-4), 1)
