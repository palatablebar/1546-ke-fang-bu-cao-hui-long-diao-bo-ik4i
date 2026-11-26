from math import fsum, sqrt


def weighted_quantile(values, fraction):
    if not values or not 0 <= fraction <= 1:
        raise ValueError('无可计算的分位点')
    ordered = sorted(values)
    total = fsum(weight for _, weight in ordered)
    if total <= 0:
        raise ValueError('邻域权重为空')
    boundary = fraction * total
    accum = 0.0
    for target, weight in ordered:
        accum += weight
        if accum >= boundary:
            return target
    return ordered[-1][0]


def fit_kernel(rows):
    ordered = tuple((record.key, record.cohort, record.values, record.outcome) for record in rows)
    inventory = sorted(record[3] for record in ordered)
    return ordered, (('可比布草批', len(ordered)), ('零缺口批', inventory.count(0)),
                     ('历史缺口下四分位', inventory[len(inventory)//4]))


def score_kernel(history, sample):
    nearby = []
    for key, cohort, measures, target in history:
        gaps = tuple((ref - value) ** 2 for ref, value in zip(measures, sample.values, strict=True))
        delta = sqrt(fsum(gaps)) + (.18 if cohort != sample.cohort else 0)
        nearby.append((delta, key, target, gaps))
    selected = sorted(nearby)[:11]
    weights = [(target, 1 / (.15 + delta)) for delta, _, target, _ in selected]
    outer = weighted_quantile(weights, .72)
    relevance = tuple(fsum(column) / len(selected) for column in zip(*(row[-1] for row in selected), strict=True))
    return outer, relevance
