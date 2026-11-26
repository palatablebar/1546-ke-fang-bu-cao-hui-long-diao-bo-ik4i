from dataclasses import replace
import json
from pathlib import Path

from .linen_cages import service as intake_service
from .floor_cycles import service as cohort_service
from .turnover_factors import service as feature_service
from .swap_quantiles import service as model_service
from .loss_coverage import service as calibration_service
from .occupancy_shift import service as monitor_service
from .laundry_transfer import service as dispatch_service
from .linen_manifest import service as audit_service
from .floor_cycles import contracts as window_contract

PRESET = Path(__file__).resolve().parents[2] / 'sample_data' / 'linen_cages_sample.json'
MODULES = (('linen_cages', '回笼笼单'),
 ('floor_cycles', '楼层班窗'),
 ('turnover_factors', '用量因素'),
 ('swap_quantiles', '缺口分位'),
 ('loss_coverage', '缺口覆盖'),
 ('occupancy_shift', '入住分组'),
 ('laundry_transfer', '调拨安排'),
 ('linen_manifest', '出车清单'))
DISPLAY = {'title': '客房布草回笼调拨',
 'object_name': '门店班次',
 'unit': '件',
 'role': '旅宿集团布草主管',
 'endpoint': 'linenroute',
 'identity': 'LINEN TRANSFER',
 'location': '同城洗涤中心 · 净布草回笼',
 'visual': '回笼到调拨流程',
 'queue': '调拨申请班次',
 'resource': '调拨班组位',
 'action': '安排同城调拨',
 'lane': 'L6',
 'field_title': '整笼调拨单'}


def open_fixture(path=PRESET):
    document = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(document, dict) or not isinstance(document.get('records'), list):
        raise ValueError('样例必须包含 records 数组')
    if len(document['records']) > 2500:
        raise ValueError('单次导入最多处理 2500 条单据')
    return document


def stage_at(index, details, records, issues=()):
    code, title = MODULES[index]
    return {'key': code, 'title': title, 'summary': details, 'records': list(records), 'errors': list(issues)}


def rows_for(plan, scored, vectors):
    by_key = {item.key: item for item in scored}
    factor_names = ('补发差额', '回车有效迟滞', '团体比重', '可用成品', '增领密度')
    order = []
    for job in plan.jobs:
        point = by_key[job.key]
        if len(point.contributions) == len(factor_names):
            reasons = sorted(zip(factor_names, point.contributions, strict=True), key=lambda val: (-abs(val[1]), val[0]))
            driver = ' · '.join(f'{key} {amount:+.2f}' for key, amount in reasons[:2])
        else:
            driver = ' · '.join(f'{amount:+.2f}' for amount in point.contributions)
        interval = ('–' if job.lower is None else f'{job.lower:.2f}–{job.upper:.2f}')
        order.append({'key': job.key, 'zone': job.cohort, 'estimate': job.estimate, 'interval': interval,
                      'state': job.state, 'cost': job.cost, 'reason': job.reason, 'evidence': job.summary,
                      'drivers': driver, 'missing': len(point.missing), 'hits': list(job.rule_hits),
                      'measurements': dict(zip(('checked_out', 'on_hand', 'truck_eta', 'towel_issue', 'wash_reject', 'concert_rooms'), point.input_values, strict=True)),
                      'unmeasured': list(point.missing), 'operations': feature_service.business_factors(vectors[job.key])})
    return order


def comparison_rows(predictions):
    return [{'单号': point.key, '分组': point.cohort, '原始估计': round(point.score, 4),
             '补值字段': len(point.missing), '偏离特征': '、'.join(point.excursions) or '—'}
            for point in predictions[:14]]


def replay_metrics(report):
    result = [{'label': '回放实绩样本', 'value': report.count}, {'label': '回放绝对误差', 'value': report.mae}]
    return result


def execute(documents, capacity=12, mode='balanced', *, as_of=96):
    if type(as_of) is not int or not 91 <= as_of <= 3650:
        raise ValueError('请输入 91 至 3650 之间的整数工日')
    if type(documents) not in (list,tuple):
        raise ValueError('提交对象应为行业单据序列')
    if not documents or len(documents)>2500:
        raise ValueError('单次提交限 1–2500 张单据')
    intake = intake_service.load_samples(iter(documents),as_of)
    timeline=window_contract.WindowRule.standard(allow_censor=False)
    windows=cohort_service.build_windows(intake.entries,replace(timeline,as_of=as_of))
    cohort_service.model_inputs(windows)
    state = feature_service.fit_features(windows.train)
    features = feature_service.transform_windows(windows,state)
    apply_stamp = state.fingerprint
    kernel = model_service.fit_model(features.train,apply_stamp)
    evaluator = lambda partition: model_service.predict(kernel,partition,apply_stamp)
    # Archive, replay and current work all use a frozen estimator.
    fitted_calibration = calibration_service.prepare_verification(evaluator(features.calibration))
    grader = lambda forum: calibration_service.validate_predictions(forum,fitted_calibration)
    evaluated=grader(evaluator(features.replay))
    scored=evaluator(features.live)
    coverage=monitor_service.coverage_by_group(features.calibration,features.live)
    baseline = monitor_service.fit_baseline(features.train,apply_stamp)
    drift = monitor_service.scan_current(baseline,features.live,apply_stamp)
    checked_live=grader(scored)
    allocation = dispatch_service.plan_jobs(checked_live,drift.domain,capacity,mode)
    closed = audit_service.close_batch(tuple(documents),intake,windows,allocation,apply_stamp,kernel.name,mode)
    performance = calibration_service.performance(evaluated)
    states = dict(closed.totals.states)
    overview = [
        {'label': '当班门店班次', 'value': len(allocation.jobs)},
        {'label': '已分派', 'value': states.get('已分派', 0)},
        {'label': '候补', 'value': states.get('候补', 0)},
        {'label': '暂停及人工判读', 'value': states.get('暂停', 0) + states.get('人工判读', 0)},
        {'label': '额度结余', 'value': allocation.balance},
    ]
    vectors = {item.key: item for item in features.live}
    row_list = rows_for(allocation, scored, vectors)
    operating_rows = dispatch_service.operating_ledger(row_list)
    overtime = calibration_service.boundary_diagnostics(evaluated, 95)
    sector = calibration_service.sector_replay(evaluated, 95)
    operating_shift = monitor_service.shop_floor_shift(features.train, features.live)
    field_evidence = audit_service.sign_field_evidence(row_list, allocation)
    features_glance = feature_service.feature_evidence(state) + feature_service.measure_review(features)
    weight_rows = [{'量测': key, '取值': value} for key, value in kernel.evidence]
    ignored = [issue.evidence() for issue in intake.issues]
    details = [
        stage_at(0, f'接收 {intake.source_rows} 条，采用 {len(intake.entries)} 条', intake_service.preliminary_evidence(intake), ignored),
        stage_at(1, f'拟合 {len(windows.train)} 条，校准 {len(windows.calibration)} 条，回放 {len(windows.replay)} 条', cohort_service.window_evidence(windows) + cohort_service.readiness_evidence(windows, as_of)),
        stage_at(2, '特征转换版本 ' + state.fingerprint, features_glance),
        stage_at(3, kernel.name, weight_rows + model_service.inspection_rows(kernel, features) + comparison_rows(scored)),
        stage_at(4, f'{fitted_calibration.method} · {performance.status} · {performance.count} 条回放实绩', calibration_service.calibration_evidence(performance) + [overtime] + sector),
        stage_at(5, f'{drift.status} · {len(drift.domain)} 张单据需外推判读', monitor_service.shift_evidence(drift, coverage) + operating_shift),
        stage_at(6, f'本班占用 {allocation.capacity-allocation.balance} / {allocation.capacity} 个工位单位', dispatch_service.action_evidence(allocation) + dispatch_service.operating_group(checked_live, allocation)),
        stage_at(7, f'处置凭证 {closed.stamp} · 额度守恒', audit_service.reconciliation_evidence(closed) + field_evidence['执行业务单']),
    ]
    details[6]['operating_rows'] = operating_rows
    details[6]['operating_title'] = '整笼调拨单'
    points = [{'label': row['key'], 'value': row['estimate'], 'state': row['state'], 'zone': row['zone'],
               'upper': row['interval'], 'cost': row['cost']} for row in sorted(row_list, key=lambda row: row['key'])]
    def estimate(vector):
        return calibration_service.check_point(model_service.predict_one(kernel, vector), fitted_calibration).estimate

    # Compare interventions against frozen features, model and calibration;
    # scenario estimates never overwrite the base ticket or its decision.
    for row in row_list:
        current = vectors[row['key']]
        row['alternatives'] = feature_service.render_interventions(current, state, estimate)
        row['joint_experiments'] = feature_service.render_joint_experiments(current,state,estimate)
    details[7]['records'].extend(audit_service.site_checklist(row_list))
    details[7]['records'].extend(audit_service.intervention_summary(row_list))
    overview_report = {'capacity' : capacity, 'mode': mode, 'as_of': as_of, 'sample_hash': closed.batch_hash,
              'policy_hash': closed.policy_hash, 'feature_stamp': state.fingerprint,
              'model': kernel.name, 'run_id': closed.stamp, 'object_name': DISPLAY['object_name'],
              'unit': DISPLAY['unit'], 'sections': details, 'flow_counts': list(states.items()),
              'measures': {'checked_out': ('当班退房', '间'),
 'on_hand': ('可发净布草', '件'),
 'truck_eta': ('送洗回车预计', 'min'),
 'towel_issue': ('毛巾追加领用', '件'),
 'wash_reject': ('待洗件剔除', '%'),
 'concert_rooms': ('团体锁定房', '间')}, 'metrics': overview, 'performance': replay_metrics(performance), 'rows': row_list, 'series': points}
    return overview_report


def preview(capacity=12, mode='balanced'):
    fixture = open_fixture()
    return execute(fixture['records'], capacity, mode, as_of=fixture['as_of'])
