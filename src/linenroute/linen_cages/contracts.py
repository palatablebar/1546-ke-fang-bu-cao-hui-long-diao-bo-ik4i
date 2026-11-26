from dataclasses import dataclass

FIELDS = {'checked_out': ('当班退房', '间', 8, 180),
 'on_hand': ('可发净布草', '件', 0, 480),
 'truck_eta': ('送洗回车预计', 'min', 15, 240),
 'towel_issue': ('毛巾追加领用', '件', 0, 155),
 'wash_reject': ('待洗件剔除', '%', 0, 23),
 'concert_rooms': ('团体锁定房', '间', 0, 110)}
LIMITS = {'result_max': 10000}


class MeasureIssue(ValueError):
    def __init__(self, field: str, code: str):
        super().__init__(f'{field}:{code}')
        self.field = field
        self.code = code


@dataclass(frozen=True, slots=True)
class LinenrouteRecord:
    key: str
    cohort: str
    day: int
    received: int
    revision: int
    result_day: int | None
    outcome: float | None
    observed: bool
    checked_out: float | None
    on_hand: float | None
    truck_eta: float | None
    towel_issue: float | None
    wash_reject: float | None
    concert_rooms: float | None

    def signature(self):
        return (self.key, self.cohort, self.day, self.revision, self.result_day, self.outcome, self.observed,
                *(getattr(self, key) for key in FIELDS))


@dataclass(frozen=True, slots=True)
class Issue:
    source_row: int
    key: str
    field: str
    code: str

    def evidence(self):
        return {'行号': self.source_row, '单号': self.key, '字段': FIELDS.get(self.field, (self.field,))[0],
                '原因': self.code}


@dataclass(frozen=True, slots=True)
class DecodeResult:
    entries: tuple[LinenrouteRecord, ...]
    issues: tuple[Issue, ...]
    source_rows: int
