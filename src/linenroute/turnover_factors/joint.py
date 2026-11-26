from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class JointAction:
    case: str
    work_units: int
    notes: str
    changes: dict[str, tuple[float, float]]

    def evidence(self, old_value, new_value, extrapolates):
        return {'联动推演':self.case, '用量':self.work_units, '先决条件':self.notes,
                '原预测':round(old_value,4), '替换预测':round(new_value,4),
                '变化':round(new_value-old_value,4), '超训练域':bool(extrapolates),
                '联动量测':{item:{'原值':before,'替换值':after} for item,(before,after) in self.changes.items()}}


def simulate_rush_clean_stock(readings, invalid):
    on_hand, truck_eta = readings[1], readings[2]
    if invalid.intersection(('on_hand', 'truck_eta')):
        return None
    if not (truck_eta>=60 and on_hand<=420):
        return None
    truck_eta_adjusted = truck_eta-40
    on_hand_adjusted = on_hand+55
    inspected = {
        'truck_eta': (truck_eta, truck_eta_adjusted),
        'on_hand': (on_hand, on_hand_adjusted),
    }
    if any(new != old for old,new in inspected.values()):
        return JointAction('同城加车和净件', 3, '把已经洗完的净件提前发出', inspected)
    return None


def simulate_phase_group_arrival(readings, invalid):
    towel_issue, concert_rooms = readings[3], readings[5]
    if invalid.intersection(('towel_issue', 'concert_rooms')):
        return None
    if not (concert_rooms>=35 and towel_issue>=25):
        return None
    concert_rooms_adjusted = concert_rooms-30
    towel_issue_adjusted = towel_issue-18
    inspected = {
        'concert_rooms': (concert_rooms, concert_rooms_adjusted),
        'towel_issue': (towel_issue, towel_issue_adjusted),
    }
    if any(new != old for old,new in inspected.values()):
        return JointAction('团房分批和暂扣领用', 2, '错开团抵窗口和额外毛巾领用', inspected)
    return None


def simulate_strengthen_sort(readings, invalid):
    on_hand, wash_reject = readings[1], readings[4]
    if invalid.intersection(('on_hand', 'wash_reject')):
        return None
    if not (wash_reject>=5 and on_hand<=440):
        return None
    wash_reject_adjusted = wash_reject-5
    on_hand_adjusted = on_hand+35
    inspected = {
        'wash_reject': (wash_reject, wash_reject_adjusted),
        'on_hand': (on_hand, on_hand_adjusted),
    }
    if any(new != old for old,new in inspected.values()):
        return JointAction('重分拣和补货', 2, '复核干品再入派车标签', inspected)
    return None


def simulate_postpone_turnover(readings, invalid):
    checked_out, truck_eta = readings[0], readings[2]
    if invalid.intersection(('checked_out', 'truck_eta')):
        return None
    if not (checked_out>=40 and truck_eta>=48):
        return None
    checked_out_adjusted = checked_out-25
    truck_eta_adjusted = truck_eta-25
    inspected = {
        'checked_out': (checked_out, checked_out_adjusted),
        'truck_eta': (truck_eta, truck_eta_adjusted),
    }
    if any(new != old for old,new in inspected.values()):
        return JointAction('本店延后清理两层', 1, '保留未入住楼层到第二班', inspected)
    return None


def simulate_protect_group_kits(readings, invalid):
    on_hand, towel_issue = readings[1], readings[3]
    if invalid.intersection(('on_hand', 'towel_issue')):
        return None
    if not (towel_issue>=22 and on_hand<=437):
        return None
    towel_issue_adjusted = towel_issue-19
    on_hand_adjusted = on_hand+32
    inspected = {
        'towel_issue': (towel_issue, towel_issue_adjusted),
        'on_hand': (on_hand, on_hand_adjusted),
    }
    if any(new != old for old,new in inspected.values()):
        return JointAction('先安排团队用品', 2, '将中心仓的套件分给团队层', inspected)
    return None


def options(values, missing):
    measurements=tuple(values)
    unobserved=frozenset(missing)
    cases=(
        simulate_rush_clean_stock(measurements, unobserved),
        simulate_phase_group_arrival(measurements, unobserved),
        simulate_strengthen_sort(measurements, unobserved),
        simulate_postpone_turnover(measurements, unobserved),
        simulate_protect_group_kits(measurements, unobserved),
    )
    return tuple(action for action in cases if action is not None)
