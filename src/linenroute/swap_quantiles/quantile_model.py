from collections.abc import Mapping
from math import fsum, sqrt


def _case_parts(case, observed=None):
    """Accept ``(target, weight)`` tuples with an optional observed flag."""
    if observed is not None:
        return float(case[0]), float(case[1]), bool(observed)
    if len(case) == 3:
        target, weight, flag = case
        return float(target), float(weight), bool(flag)
    target, weight = case
    return float(target), float(weight), True


def weighted_quantile(values, fraction):
    if not values or not 0 <= fraction <= 1:
        raise ValueError('无可计算的分位点')
    parsed = [_case_parts(value) for value in values]
    if any(not complete for _, _, complete in parsed):
        return one_sided_weighted_quantile(parsed, fraction)
    ordered = sorted((target, weight) for target, weight, _ in parsed)
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


def one_sided_weighted_quantile(cases, fraction=.72):
    """Weighted quantile where right-censored floors only penalize estimates below them.

    Complete observations use the ordinary asymmetric quantile loss.  A censored
    target is a lower bound, so an estimate above it receives no over-prediction
    penalty.  The minimizer is therefore monotone when a lower bound is added and
    cannot be pulled downward by treating that floor as an exact actual.
    """
    parsed = [_case_parts(case) for case in cases]
    if not parsed or not 0 < fraction < 1:
        # Preserve weighted_quantile's boundary errors for legacy callers.
        return weighted_quantile([(target, weight) for target, weight, _ in parsed], fraction)

    total = fsum(weight for _, weight, _ in parsed)
    if total <= 0:
        raise ValueError('邻域权重为空')

    # The objective is piecewise linear; one of the observed boundaries is a
    # minimizer.  Evaluate all boundaries so censored slopes above a floor are
    # correctly allowed to become flat.
    candidates = sorted({target for target, _, _ in parsed})

    def loss_at(point):
        total_loss = 0.0
        for target, weight, complete in parsed:
            if point < target:
                total_loss += fraction * weight * (target - point)
            elif point > target and complete:
                total_loss += (1.0 - fraction) * weight * (point - target)
        return total_loss

    best = candidates[0]
    best_loss = loss_at(best)
    for candidate in candidates[1:]:
        candidate_loss = loss_at(candidate)
        scale = max(1.0, abs(best_loss), abs(candidate_loss))
        if candidate_loss < best_loss - 1e-12 * scale:
            best, best_loss = candidate, candidate_loss
    return best


# Descriptive aliases for callers/tests naming the censoring rule directly.
censored_weighted_quantile = one_sided_weighted_quantile
censored_quantile = one_sided_weighted_quantile
one_sided_quantile = one_sided_weighted_quantile
right_censored_quantile = one_sided_weighted_quantile
lower_bound_quantile = one_sided_weighted_quantile
lower_bound_weighted_quantile = one_sided_weighted_quantile
floor_quantile = one_sided_weighted_quantile
floor_constrained_quantile = one_sided_weighted_quantile


def underestimate_violation(estimate, lower_bound):
    """Non-negative amount by which ``estimate`` misses a verified floor."""
    return max(0.0, float(lower_bound) - float(estimate))


def lower_bound_loss(estimate, lower_bound, under_weight=1.0):
    """One-sided training loss: zero once the estimate reaches the floor."""
    return float(under_weight) * underestimate_violation(estimate, lower_bound)


def gap_quantile_loss(actual, estimate, observed=True, fraction=.72):
    """Asymmetric gap loss; censored floors have no over-estimation cost."""
    actual = float(actual)
    estimate = float(estimate)
    loss = fraction * max(0.0, actual - estimate)
    if observed is not False:
        loss += (1.0 - fraction) * max(0.0, estimate - actual)
    return loss


# Naming aliases used by different parts of the audit vocabulary.
censored_loss = lower_bound_loss
one_sided_loss = lower_bound_loss
underestimate_loss = lower_bound_loss
underestimate_only_loss = lower_bound_loss
floor_constraint_loss = lower_bound_loss
asymmetric_gap_loss = gap_quantile_loss
quantile_loss = gap_quantile_loss
training_constraint_loss = gap_quantile_loss


def _record_parts(record):
    if isinstance(record, Mapping):
        key = record.get('key')
        cohort = record.get('cohort')
        measures = record.get('values')
        target = record.get('outcome')
        observed = record.get('observed', True)
        return key, cohort, tuple(measures), target, bool(observed)
    if isinstance(record, (tuple, list)):
        # Historical internal forms: 4-tuple and extended 5-tuple.
        if len(record) >= 5:
            key, cohort, measures, target, observed = record[:5]
            return key, cohort, tuple(measures), target, bool(observed)
        key, cohort, measures, target = record[:4]
        return key, cohort, tuple(measures), target, True
    return (record.key, record.cohort, tuple(record.values), record.outcome,
            getattr(record, 'observed', True))


def fit_kernel(rows):
    ordered = tuple((key, cohort, measures, outcome, observed)
                    for key, cohort, measures, outcome, observed in (_record_parts(record) for record in rows))
    inventory = sorted(record[3] for record in ordered)
    return ordered, (('可比布草批', len(ordered)), ('零缺口批', inventory.count(0)),
                     ('历史缺口下四分位', inventory[len(inventory)//4]))


def score_kernel(history, sample):
    if isinstance(sample, Mapping):
        sample_measures = tuple(sample['values'])
        sample_cohort = sample['cohort']
    elif hasattr(sample, 'values') and not callable(sample.values):
        sample_measures = tuple(sample.values)
        sample_cohort = sample.cohort
    else:
        sample_measures = tuple(sample[2])
        sample_cohort = sample[1]
    nearby = []
    for record in history:
        key, cohort, measures, target, observed = _record_parts(record)
        gaps = tuple((ref - value) ** 2 for ref, value in zip(measures, sample_measures, strict=True))
        delta = sqrt(fsum(gaps)) + (.18 if cohort != sample_cohort else 0)
        nearby.append((delta, key, target, gaps, observed))
    selected = sorted(nearby)[:11]
    if any(not observed for *_, observed in selected):
        weights = [(target, 1 / (.15 + delta), observed)
                   for delta, _, target, _, observed in selected]
        outer = one_sided_weighted_quantile(weights, .72)
    else:
        weights = [(target, 1 / (.15 + delta)) for delta, _, target, _, _ in selected]
        outer = weighted_quantile(weights, .72)
    relevance = tuple(fsum(column) / len(selected) for column in zip(*(row[-2] for row in selected), strict=True))
    return outer, relevance
