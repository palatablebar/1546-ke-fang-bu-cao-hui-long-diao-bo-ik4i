from dataclasses import replace
from statistics import mean, median
from collections import Counter
from math import fsum

from .contracts import FEATURE_NAMES, FEATURE_KEYS, RAW_KEYS


def current_minimum_reset(vector):
    checked_out = vector.input_values[0]
    return float(2*checked_out)


def compare_minimum_reset(training, target):
    usual_minimum_reset = take_sample(training, current_minimum_reset)
    recent_minimum_reset = take_sample(target, current_minimum_reset)
    if len(usual_minimum_reset) < 4 or not recent_minimum_reset:
        return {'作业量': '退房最低换套件', '有效读数': len(recent_minimum_reset), '判断': '参考不足'}
    anchor_minimum_reset = median(usual_minimum_reset)
    measured_minimum_reset = median(recent_minimum_reset)
    band_minimum_reset = max(1.0, abs(anchor_minimum_reset)*.2, median(abs(value-anchor_minimum_reset) for value in usual_minimum_reset))
    change_minimum_reset = (measured_minimum_reset-anchor_minimum_reset) / band_minimum_reset
    outside_minimum_reset = sum(abs(value-anchor_minimum_reset)>2.5*band_minimum_reset for value in recent_minimum_reset)
    return {'作业量': '退房最低换套件', '训练参考': round(anchor_minimum_reset, 4), '现场中位': round(measured_minimum_reset, 4),
            '变动': round(change_minimum_reset, 4), '越界量': outside_minimum_reset, '有效读数': len(recent_minimum_reset)}


def current_clean_margin(vector):
    checked_out = vector.input_values[0]
    on_hand = vector.input_values[1]
    towel_issue = vector.input_values[3]
    return float(on_hand-2*checked_out-towel_issue)


def compare_clean_margin(training, target):
    usual_clean_margin = take_sample(training, current_clean_margin)
    recent_clean_margin = take_sample(target, current_clean_margin)
    if len(usual_clean_margin) < 4 or not recent_clean_margin:
        return {'作业量': '基础布草减发后库存', '有效读数': len(recent_clean_margin), '判断': '参考不足'}
    anchor_clean_margin = median(usual_clean_margin)
    measured_clean_margin = median(recent_clean_margin)
    ordered_clean_margin = sorted(usual_clean_margin)
    low_clean_margin, high_clean_margin = ordered_clean_margin[len(ordered_clean_margin)//10], ordered_clean_margin[(len(ordered_clean_margin)*9)//10]
    change_clean_margin = measured_clean_margin-anchor_clean_margin
    outside_clean_margin = sum(value<low_clean_margin or value>high_clean_margin for value in recent_clean_margin)
    return {'作业量': '基础布草减发后库存', '训练参考': round(anchor_clean_margin, 4), '现场中位': round(measured_clean_margin, 4),
            '变动': round(change_clean_margin, 4), '越界量': outside_clean_margin, '有效读数': len(recent_clean_margin)}


def current_shortage_risk(vector):
    checked_out = vector.input_values[0]
    on_hand = vector.input_values[1]
    towel_issue = vector.input_values[3]
    concert_rooms = vector.input_values[5]
    return float(max(0,2*checked_out+towel_issue+2*concert_rooms-on_hand))


def compare_shortage_risk(training, target):
    usual_shortage_risk = take_sample(training, current_shortage_risk)
    recent_shortage_risk = take_sample(target, current_shortage_risk)
    if len(usual_shortage_risk) < 4 or not recent_shortage_risk:
        return {'作业量': '到店前未覆盖份数', '有效读数': len(recent_shortage_risk), '判断': '参考不足'}
    anchor_shortage_risk = median(usual_shortage_risk)
    measured_shortage_risk = median(recent_shortage_risk)
    band_shortage_risk = max(1.0, abs(anchor_shortage_risk)*.2, median(abs(value-anchor_shortage_risk) for value in usual_shortage_risk))
    change_shortage_risk = (measured_shortage_risk-anchor_shortage_risk) / band_shortage_risk
    outside_shortage_risk = sum(abs(value-anchor_shortage_risk)>2.5*band_shortage_risk for value in recent_shortage_risk)
    return {'作业量': '到店前未覆盖份数', '训练参考': round(anchor_shortage_risk, 4), '现场中位': round(measured_shortage_risk, 4),
            '变动': round(change_shortage_risk, 4), '越界量': outside_shortage_risk, '有效读数': len(recent_shortage_risk)}


def current_margin_minutes(vector):
    truck_eta = vector.input_values[2]
    return float(240-truck_eta)


def compare_margin_minutes(training, target):
    usual_margin_minutes = take_sample(training, current_margin_minutes)
    recent_margin_minutes = take_sample(target, current_margin_minutes)
    if len(usual_margin_minutes) < 4 or not recent_margin_minutes:
        return {'作业量': '距四小时洗回', '有效读数': len(recent_margin_minutes), '判断': '参考不足'}
    anchor_margin_minutes = median(usual_margin_minutes)
    measured_margin_minutes = median(recent_margin_minutes)
    ordered_margin_minutes = sorted(usual_margin_minutes)
    low_margin_minutes, high_margin_minutes = ordered_margin_minutes[len(ordered_margin_minutes)//10], ordered_margin_minutes[(len(ordered_margin_minutes)*9)//10]
    change_margin_minutes = measured_margin_minutes-anchor_margin_minutes
    outside_margin_minutes = sum(value<low_margin_minutes or value>high_margin_minutes for value in recent_margin_minutes)
    return {'作业量': '距四小时洗回', '训练参考': round(anchor_margin_minutes, 4), '现场中位': round(measured_margin_minutes, 4),
            '变动': round(change_margin_minutes, 4), '越界量': outside_margin_minutes, '有效读数': len(recent_margin_minutes)}


def current_cart_utility(vector):
    on_hand = vector.input_values[1]
    wash_reject = vector.input_values[4]
    return float(on_hand*(1-wash_reject/100)/2)


def compare_cart_utility(training, target):
    usual_cart_utility = take_sample(training, current_cart_utility)
    recent_cart_utility = take_sample(target, current_cart_utility)
    if len(usual_cart_utility) < 4 or not recent_cart_utility:
        return {'作业量': '当前库存可开套数', '有效读数': len(recent_cart_utility), '判断': '参考不足'}
    anchor_cart_utility = median(usual_cart_utility)
    measured_cart_utility = median(recent_cart_utility)
    band_cart_utility = max(1.0, abs(anchor_cart_utility)*.2, median(abs(value-anchor_cart_utility) for value in usual_cart_utility))
    change_cart_utility = (measured_cart_utility-anchor_cart_utility) / band_cart_utility
    outside_cart_utility = sum(abs(value-anchor_cart_utility)>2.5*band_cart_utility for value in recent_cart_utility)
    return {'作业量': '当前库存可开套数', '训练参考': round(anchor_cart_utility, 4), '现场中位': round(measured_cart_utility, 4),
            '变动': round(change_cart_utility, 4), '越界量': outside_cart_utility, '有效读数': len(recent_cart_utility)}


def current_resupply_cost(vector):
    checked_out = vector.input_values[0]
    towel_issue = vector.input_values[3]
    return float(towel_issue/(1+checked_out))


def compare_resupply_cost(training, target):
    usual_resupply_cost = take_sample(training, current_resupply_cost)
    recent_resupply_cost = take_sample(target, current_resupply_cost)
    if len(usual_resupply_cost) < 4 or not recent_resupply_cost:
        return {'作业量': '每间库存周转需求', '有效读数': len(recent_resupply_cost), '判断': '参考不足'}
    anchor_resupply_cost = median(usual_resupply_cost)
    measured_resupply_cost = median(recent_resupply_cost)
    ordered_resupply_cost = sorted(usual_resupply_cost)
    low_resupply_cost, high_resupply_cost = ordered_resupply_cost[len(ordered_resupply_cost)//10], ordered_resupply_cost[(len(ordered_resupply_cost)*9)//10]
    change_resupply_cost = measured_resupply_cost-anchor_resupply_cost
    outside_resupply_cost = sum(value<low_resupply_cost or value>high_resupply_cost for value in recent_resupply_cost)
    return {'作业量': '每间库存周转需求', '训练参考': round(anchor_resupply_cost, 4), '现场中位': round(measured_resupply_cost, 4),
            '变动': round(change_resupply_cost, 4), '越界量': outside_resupply_cost, '有效读数': len(recent_resupply_cost)}


def current_wash_discard(vector):
    checked_out = vector.input_values[0]
    on_hand = vector.input_values[1]
    wash_reject = vector.input_values[4]
    return float((on_hand+2*checked_out)*wash_reject/100)


def compare_wash_discard(training, target):
    usual_wash_discard = take_sample(training, current_wash_discard)
    recent_wash_discard = take_sample(target, current_wash_discard)
    if len(usual_wash_discard) < 4 or not recent_wash_discard:
        return {'作业量': '近似剔除件数', '有效读数': len(recent_wash_discard), '判断': '参考不足'}
    anchor_wash_discard = median(usual_wash_discard)
    measured_wash_discard = median(recent_wash_discard)
    band_wash_discard = max(1.0, abs(anchor_wash_discard)*.2, median(abs(value-anchor_wash_discard) for value in usual_wash_discard))
    change_wash_discard = (measured_wash_discard-anchor_wash_discard) / band_wash_discard
    outside_wash_discard = sum(abs(value-anchor_wash_discard)>2.5*band_wash_discard for value in recent_wash_discard)
    return {'作业量': '近似剔除件数', '训练参考': round(anchor_wash_discard, 4), '现场中位': round(measured_wash_discard, 4),
            '变动': round(change_wash_discard, 4), '越界量': outside_wash_discard, '有效读数': len(recent_wash_discard)}


def current_block_cover(vector):
    concert_rooms = vector.input_values[5]
    return float(concert_rooms*2)


def compare_block_cover(training, target):
    usual_block_cover = take_sample(training, current_block_cover)
    recent_block_cover = take_sample(target, current_block_cover)
    if len(usual_block_cover) < 4 or not recent_block_cover:
        return {'作业量': '团抵所需净布草', '有效读数': len(recent_block_cover), '判断': '参考不足'}
    anchor_block_cover = median(usual_block_cover)
    measured_block_cover = median(recent_block_cover)
    ordered_block_cover = sorted(usual_block_cover)
    low_block_cover, high_block_cover = ordered_block_cover[len(ordered_block_cover)//10], ordered_block_cover[(len(ordered_block_cover)*9)//10]
    change_block_cover = measured_block_cover-anchor_block_cover
    outside_block_cover = sum(value<low_block_cover or value>high_block_cover for value in recent_block_cover)
    return {'作业量': '团抵所需净布草', '训练参考': round(anchor_block_cover, 4), '现场中位': round(measured_block_cover, 4),
            '变动': round(change_block_cover, 4), '越界量': outside_block_cover, '有效读数': len(recent_block_cover)}


def take_sample(vectors, measure):
    return tuple(measure(record) for record in vectors if not record.missing)


def measure_turnover_factors_band(history, daybook):
    yield compare_minimum_reset(history, daybook)
    yield compare_clean_margin(history, daybook)
    yield compare_shortage_risk(history, daybook)
    yield compare_margin_minutes(history, daybook)
    yield compare_cart_utility(history, daybook)
    yield compare_resupply_cost(history, daybook)
    yield compare_wash_discard(history, daybook)
    yield compare_block_cover(history, daybook)


def evaluate_shift(training, current):
    return list(measure_turnover_factors_band(training, current))
