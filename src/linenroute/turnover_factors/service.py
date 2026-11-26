from dataclasses import replace
from hashlib import blake2s
from math import fsum, isfinite, sqrt
from statistics import median, quantiles

from .measurement_bands import evaluate_shift
from .contracts import PreparedRuns, FeatureState, FeatureVector, FEATURE_KEYS, RAW_KEYS


def spread(samples):
    offset = median(samples)
    portions = [abs(item-offset) for item in samples]
    sigma = median(portions)*1.4826
    if sigma < 1e-9:
        basis = fsum((value-offset)**2 for value in samples) / len(samples)
        sigma = sqrt(basis) or 1.
    return offset,sigma


def derive(values):
    checked_out, on_hand, truck_eta, towel_issue, wash_reject, concert_rooms = values
    service_pressure = checked_out*2+towel_issue-on_hand
    eta_risk = truck_eta/60*(1+wash_reject/15)
    block_ratio = concert_rooms/(checked_out+10)
    usable_linen = on_hand*(1-wash_reject/100)
    resupply_density = towel_issue/(checked_out+1)
    return service_pressure, eta_risk, block_ratio, usable_linen, resupply_density


def fit_features(training):
    stable = tuple(sorted(training,key=lambda note:note.key))
    if not stable:
        raise ValueError('缺少历史量测')
    replacements = []
    for key in RAW_KEYS:
        column = [getattr(note,key) for note in stable]
        valid = [value for value in column if value is not None]
        if not valid:
            raise ValueError(f'无法为 {key} 估计稳健中心')
        replacements.append(median(valid))
    data = [derive(record_values(note,replacements)[0]) for note in stable]
    guides = [spread(numbers) for numbers in zip(*data,strict=True)]
    limits = tuple(zip(*data,strict=True))
    revision = blake2s(repr((FEATURE_KEYS,replacements,guides,[item.signature() for item in stable])).encode(),digest_size=8).hexdigest()
    return FeatureState(tuple(replacements),tuple(row[0] for row in guides),tuple(row[1] for row in guides),
                        tuple(min(table) for table in limits),tuple(max(table) for table in limits),revision)


def record_values(record, substitutes):
    absent = []
    numbers = []
    for field,value in zip(RAW_KEYS,substitutes,strict=True):
        reading = getattr(record,field)
        if reading is None:
            absent.append(field)
            reading = value
        numbers.append(reading)
    return tuple(numbers),tuple(absent)


def numeric_fields(raw, reference):
    figures = derive(raw)
    normalized = tuple((measure-base)/band for measure,base,band in zip(figures,reference.offsets,reference.scales,strict=True))
    if any(not isfinite(amount) for amount in normalized):
        raise ValueError('出现不可缩放的量测')
    mask = tuple(name for name, standard, lo,hi,delta in zip(FEATURE_KEYS,figures,reference.floor,reference.ceil,reference.scales,strict=True)
                 if standard + .80*delta < lo or standard - .80*delta > hi)
    return normalized,figures,mask


def transform(observation, reference):
    record, omissions = record_values(observation,reference.fill)
    scaled, figures, masked = numeric_fields(record,reference)
    return FeatureVector(key=observation.key,cohort=observation.cohort,day=observation.day,values=scaled,factors=figures,
                         missing=omissions,excursions=masked,outcome=observation.outcome,observed=observation.observed,input_values=record)


def transform_all(observations, reference):
    packed = []
    for measurement in observations:
        packed.append(transform(measurement,reference))
    return tuple(packed)


def transform_windows(windows, reference):
    return PreparedRuns(*(transform_all(records, reference) for _, records in windows.partitions()))


def feature_evidence(reference):
    return [{'特征': name,'中心':round(center,3),'尺度':round(scale,3),'训练最小':round(low,3),'训练最大':round(high,3)}
            for name,center,scale,low,high in zip(FEATURE_KEYS,reference.offsets,reference.scales,reference.floor,reference.ceil,strict=True)]


def render_interventions(vector, reference, score):
    from .interventions import propose_laundry_transfer

    records = []
    estimate = score(vector)
    for adjustment in propose_laundry_transfer(vector.input_values, vector.missing):
        position=RAW_KEYS.index(adjustment.field)
        modified=tuple(adjustment.after if position==slot else part for slot,part in enumerate(vector.input_values))
        values, factors, flags = numeric_fields(modified,reference)
        alternative=replace(vector,values=values,factors=factors,input_values=modified,excursions=flags)
        revised=score(alternative)
        records.append({**adjustment.evidence(),'原预测':round(estimate,4),'替换预测':round(revised,4),
                        '预测变化':round(revised-estimate,4),'超训练域':bool(flags)})
    return records


def business_factors(vector):
    from .interventions import measure_turnover_factors

    return measure_turnover_factors(vector.input_values).explain()


def measure_review(features):
    return evaluate_shift(features.train, features.live)


def render_joint_experiments(vector, reference, score):
    from .joint import options

    raw = vector.input_values
    base = score(vector)
    replies=[]
    for action in options(raw,vector.missing):
        adjusted = tuple(action.changes[key][1] if key in action.changes else value for key,value in zip(RAW_KEYS,raw,strict=True))
        normalized, measured, signals=numeric_fields(adjusted,reference)
        scenario=replace(vector,values=normalized,input_values=adjusted,factors=measured,excursions=signals)
        replies.append(action.evidence(base,score(scenario),signals))
    return replies
