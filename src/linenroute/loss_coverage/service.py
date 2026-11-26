from math import ceil, isfinite, sqrt
from statistics import mean

from .contracts import Verification, Assessment, ModelReport
from .slices import replay_slices


def physical_residual_scale(point):
    return max(5., sqrt(point.input_values[0]+1))


def ranked_error(samples, coverage):
    if not 0 < coverage < 1:
        raise ValueError('区间比例应在零和一之间')
    ordered = sorted(samples)
    if not ordered:
        return None
    order = min(len(ordered)-1,ceil((len(ordered)+1)*coverage)-1)
    return ordered[order]


def scarcity_tail(entries, assurance):
    scaled = []
    for observation in entries:
        denom = physical_residual_scale(observation)
        scaled.append((observation.score - observation.outcome) / denom)
    inside = ranked_error([max(0,x) for x in scaled], max(assurance,.77))
    outside = ranked_error([max(0,-x) for x in scaled], max(assurance,.92))
    return (inside,outside)


def prepare_verification(pairs, *, coverage=.85):
    known = [item for item in pairs if item.outcome is not None and item.observed]
    if any(not isfinite(ticket.score) or not isfinite(ticket.outcome) for ticket in known):
        raise ValueError('区间估计要求有限的实绩和模型输出')
    if not known:
        return Verification('sparse-interval',(),0,None)
    return Verification('scarcity_tail',scarcity_tail(known,coverage),len(known),None)


def check_point(scored, bounds):
    if not isfinite(scored.score) or scored.score < 0:
        raise ValueError('连续预测必须为非负有限值')
    if not bounds.parameters:
        return Assessment(scored,scored.score,None,None,True)
    inner, outer = bounds.parameters
    scale = physical_residual_scale(scored)
    return Assessment(scored,scored.score,max(0.,scored.score-inner*scale),
                      scored.score+outer*scale,False)


def validate_predictions(scored, prepared):
    return tuple(check_point(record, prepared) for record in scored)


def performance(assessments):
    differences = []
    covered = []
    for view in assessments:
        outcome = view.raw.outcome
        if outcome is None or not view.raw.observed:
            continue
        differences.append(view.estimate - outcome)
        if view.lower is not None:
            covered.append(view.lower<=outcome<=view.upper)
    if not differences:
        return ModelReport('NO_MATURE_RESULT',0,None,None,(),None)
    return ModelReport('READY',len(differences),mean(map(abs,differences)),
                       sqrt(mean(delta**2 for delta in differences)),(),mean(covered) if covered else None)


def calibration_evidence(report):
    return [{'核验':report.status,'样本':report.count,'平均绝对误差':report.mae,
             '均方根误差':report.error,'区间覆盖':report.auxiliary}]


def sector_replay(checked, line):
    return replay_slices(checked,line,risk_model=False)


def _review_parts(review):
    if isinstance(review, dict) and 'raw' in review:
        raw = review['raw']
        estimate = review.get('estimate', review.get('score'))
    else:
        raw = getattr(review, 'raw', review)
        estimate = getattr(review, 'estimate', None)
        if estimate is None:
            estimate = getattr(review, 'score', None)
    estimate_value = None if estimate is None else float(estimate)

    if isinstance(raw, dict):
        observed = raw.get('observed', True)
        outcome = raw.get('outcome')
        if outcome is None:
            for key in ('lower_bound', 'gap_lower', 'lower_floor', 'floor'):
                if key in raw:
                    outcome = raw[key]
                    break
        return raw, estimate_value, outcome, bool(observed)

    observed = getattr(raw, 'observed', True)
    outcome = getattr(raw, 'outcome', None)
    if outcome is None:
        for key in ('lower_bound', 'gap_lower', 'lower_floor', 'floor'):
            if hasattr(raw, key):
                outcome = getattr(raw, key)
                break
    return raw, estimate_value, outcome, bool(observed)


def boundary_diagnostics(checks, threshold):
    missed = high = above = seen = pending = floor_over_line = floor_missed = 0
    actual_missed = 0
    for review in checks:
        _, estimate, measured, observed = _review_parts(review)
        if not observed and measured is None:
            pending += 1
            continue
        if measured is None or estimate is None:
            continue
        if observed:
            above += measured>=threshold
            seen += estimate>=threshold
            is_missed = estimate<threshold<=measured
            missed += is_missed
            actual_missed += is_missed
            high += measured<threshold<=estimate
        else:
            # ``measured`` is a verified lower bound, not a complete actual.
            # A floor at/over the line proves a miss when the estimate is below
            # it.  A floor below the line cannot clear or condemn the ticket;
            # keep it pending until the complete result is verified.
            if measured >= threshold:
                floor_over_line += 1
                is_floor_missed = estimate < threshold
                floor_missed += is_floor_missed
                missed += is_floor_missed
            else:
                pending += 1
    return {'临界判断':'布草缺供', '实绩超线':above, '估计超线':seen, '额外复测':high, '漏查':missed,
            '实绩漏查':actual_missed, '下界漏查':floor_missed,
            '下界超线':floor_over_line, '待核实':pending, '留待核实':pending,
            '待核验':pending, '留待核验':pending, 'pending_verification':pending,
            '下界未达线':pending, '未决下界':pending}


replay_boundary_diagnostics = boundary_diagnostics
censored_boundary_diagnostics = boundary_diagnostics
censored_replay_diagnostics = boundary_diagnostics
lower_bound_replay = boundary_diagnostics
review_lower_bounds = boundary_diagnostics
