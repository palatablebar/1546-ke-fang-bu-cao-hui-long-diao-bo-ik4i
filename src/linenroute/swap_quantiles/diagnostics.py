from math import exp, log, fsum, sqrt
from statistics import median, mean, quantiles

from .quantile_model import score_kernel



def explain_swap_quantiles(fit, calibration, replay, live):
    local_inventory = fit.parameters
    allocation = []
    for record in replay:
        if record.outcome is None:
            continue
        estimate, _ = score_kernel(local_inventory,record)
        local_stock = record.input_values[1]
        expected = max(0.0, 2.0*record.input_values[0]+record.input_values[3]-local_stock)
        score_cost = max(0,record.outcome-estimate)*.72 + max(0,estimate-record.outcome)*.28
        baseline_cost = max(0,record.outcome-expected)*.72 + max(0,expected-record.outcome)*.28
        allocation.append((local_stock,score_cost,baseline_cost,estimate<record.outcome))
    report = []
    for floor, ceiling in ((0,100),(100,230),(230,350),(350,481)):
        found = [row for row in allocation if floor <= row[0] < ceiling]
        if found:
            report.append({'净件库存窗':f'{floor}–{ceiling}','回笼班数':len(found),'缺口分位损失':round(mean(row[1] for row in found),2),
                           '简单库存损失':round(mean(row[2] for row in found),2),'低估缺口班次':sum(row[3] for row in found)})
    return report
