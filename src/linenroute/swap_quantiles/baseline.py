from collections import defaultdict
from math import fabs, fsum
from statistics import mean, median

from .quantile_model import score_kernel


def stock_adjustment(data):
    deltas = []
    for shift in data:
        # The static baseline is calibrated from complete actuals.  A lower
        # bound would otherwise be treated as an exact replenishment result.
        if not getattr(shift, 'observed', True) or shift.outcome is None:
            continue
        minimum = max(0,2*shift.input_values[0]+shift.input_values[3]-shift.input_values[1])
        deltas.append(shift.outcome-minimum)
    if not deltas:
        return 0.0
    return sorted(deltas)[int((len(deltas)-1)*.72)]


def basic_inventory(offset,shift):
    outgoing, stock, _, requests, *_ = shift.input_values
    return max(0,2*outgoing + requests-stock+offset)


def baseline_review(fit, training, replay):
    convention = stock_adjustment(training)
    production = defaultdict(list)
    for sample in replay:
        if not sample.observed or sample.outcome is None:
            continue
        estimate, _ = score_kernel(fit.parameters,sample)
        baseline = basic_inventory(convention, sample)
        actual = sample.outcome
        loss, prior = max(0,actual-estimate)*.72+max(0,estimate-actual)*.28,max(0,actual-baseline)*.72+max(0,baseline-actual)*.28
        production[sample.cohort].append((loss,prior,estimate-actual,baseline-actual))
    reports = []
    for sector, comparison in sorted(production.items()):
        model_loss, base_loss, error, original = zip(*comparison,strict=True)
        paired = tuple(old-new for old,new in zip(base_loss,model_loss,strict=True))
        n = len(comparison)
        reports.append({'回放组':sector,'实绩数':n,'基线':'排除车次的静态件数估计','估计代价':round(mean(model_loss),4),
                        '业务基线代价':round(mean(base_loss),4),'模型偏误中位':round(median(error),4),
                        '参照偏误中位':round(median(original),4),'同单误差减少中位':round(median(paired),4),
                        '改善单数':sum(delta>0 for delta in paired),'恶化单数':sum(delta<0 for delta in paired)})
    return reports
