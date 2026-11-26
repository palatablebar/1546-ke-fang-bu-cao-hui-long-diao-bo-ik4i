from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Callable

from .contracts import Job


@dataclass(frozen=True, slots=True)
class WorkOrder:
    job: Job
    assessment: Any

    def __post_init__(self):
        if self.job.key != self.assessment.raw.key:
            raise ValueError('处置工位与单据不匹配')


def apply_laundry_transfer(transfers, admit: Callable, wait: Callable):
    vans = Counter()
    urgent = sorted(transfers, key=lambda item: (not bool(item.job.rule_hits), -item.assessment.raw.input_values[-1], -item.job.priority, item.job.key))
    for cage in urgent:
        rooms, clean, eta, towels, rejected, group = cage.assessment.raw.input_values
        wave = int(eta / 45)
        demand = max(0, int(rooms*2+towels+group*2-clean))
        if demand > 0 and vans[wave] >= 5:
            wait(cage, 'TRANSFER_WINDOW_BOOKED', '本回车时间窗已合并五批')
            continue
        if rejected > 18 and clean >= 150:
            wait(cage, 'SORT_STOCK_FIRST', '先确认能用的库存再占车')
        elif admit(cage):
            vans[wave] += 1
