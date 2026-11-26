from dataclasses import replace
import pytest
from linenroute.laundry_transfer.contracts import RISK_CUTOFF, Policy
from linenroute.laundry_transfer.service import confidence_weight, plan_jobs, recommend
from linenroute.loss_coverage.contracts import Assessment


def test_hard_rule_precedes_outside_reference(prediction):
    # TRAP-19
    raw = replace(prediction, input_values=(151, 22, 150, 80, 15, 70))
    graded = Assessment(raw,RISK_CUTOFF*2,None,None,True)
    decision = recommend(graded,{raw.key},Policy.select(12,'balanced'))
    assert decision.state == '暂停' and decision.reason == 'CLEAN_STOCKOUT'
    assert decision.rule_hits[0] == 'CLEAN_STOCKOUT'


def test_capacity_never_increases_on_dispatch(prediction):
    records = [Assessment(replace(prediction,key=str(i),input_values=(94.0, 240.0, 127.5, 77.5, 11.5, 55.0)),RISK_CUTOFF*2,None,None,False) for i in range(8)]
    resolved = plan_jobs(records,(),5,'focus')
    used = sum(item.cost for item in resolved.jobs if item.state == '已分派')
    assert resolved.balance + used == resolved.capacity == 5
    assert used > 0


def test_frontier_rejection_requires_manual_review(prediction):
    assessments = [Assessment(prediction,RISK_CUTOFF*2,None,None,True)]
    report = plan_jobs(assessments,[prediction.key],8)
    assert report.jobs[0].state in {'人工判读','暂停'}
    assert report.balance == 8


def test_round_robin_group_budget_prevents_starvation(prediction):
    records = [Assessment(replace(prediction,key=f't{i}',input_values=(94.0, 240.0, 127.5, 77.5, 11.5, 55.0)),RISK_CUTOFF*2,None,None,False) for i in range(10)]
    plan = plan_jobs(records,(),12)
    assert len(plan.used_by_group) == 1
    assert all(used <= Policy.select(12,'balanced').group_quota for _,used in plan.used_by_group)


def test_critical_weight_is_stable_for_large_estimates():
    assert confidence_weight(1e200,1) == 1
    assert confidence_weight(-1e200,1) == 0
    assert confidence_weight(1,1) == .5


def test_policy_rejects_invalid_strategy():
    with pytest.raises(ValueError,match='策略'):
        Policy.select(10,'unlisted')
    with pytest.raises(ValueError,match='额度'):
        Policy.select(True,'focus')


def test_duplicate_stage_work_rejected(prediction):
    request = Assessment(prediction,RISK_CUTOFF*2,None,None,False)
    with pytest.raises(ValueError,match='重复'):
        plan_jobs([request,request],(),12)
