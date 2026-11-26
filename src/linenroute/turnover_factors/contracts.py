from dataclasses import dataclass
from math import isfinite
from ..linen_cages.contracts import LinenrouteRecord as RawObservation

RAW_KEYS = ('checked_out', 'on_hand', 'truck_eta', 'towel_issue', 'wash_reject', 'concert_rooms')
FEATURE_KEYS = ('service_pressure', 'eta_risk', 'block_ratio', 'usable_linen', 'resupply_density')
FEATURE_NAMES = ('补发差额', '回车有效迟滞', '团体比重', '可用成品', '增领密度')


@dataclass(frozen=True, slots=True)
class FeatureState:
    fill: tuple[float, ...]
    offsets: tuple[float, ...]
    scales: tuple[float, ...]
    floor: tuple[float, ...]
    ceil: tuple[float, ...]
    fingerprint: str

    def __post_init__(self):
        if len(self.fill) != len(RAW_KEYS):
            raise ValueError('补值向量维数与字段表不匹配')
        if any(len(column) != len(FEATURE_KEYS) for column in (self.offsets, self.scales, self.floor, self.ceil)):
            raise ValueError('特征状态维数不匹配')
        if min(self.scales) <= 0:
            raise ValueError('特征尺度必须为正')


@dataclass(frozen=True, slots=True)
class FeatureVector:
    key: str
    cohort: str
    day: int
    values: tuple[float, ...]
    factors: tuple[float, ...]
    missing: tuple[str, ...]
    excursions: tuple[str, ...]
    outcome: float | None
    observed: bool
    input_values: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class PreparedRuns:
    train: tuple[FeatureVector, ...]
    calibration: tuple[FeatureVector, ...]
    replay: tuple[FeatureVector, ...]
    live: tuple[FeatureVector, ...]

    def segments(self):
        return tuple((name, getattr(self, name)) for name in ('train', 'calibration', 'replay', 'live'))


@dataclass(frozen=True, slots=True)
class Proposal:
    name: str
    field: str
    before: float
    after: float
    work: int

    def __post_init__(self):
        if self.before == self.after or not isfinite(self.after) or self.work < 0:
            raise ValueError('推演动作需要实质变动和有效额度')

    def evidence(self):
        return {'情形': self.name, '变更项': self.field, '原值': self.before,
                '置换值': self.after, '用量': self.work}

@dataclass(frozen=True, slots=True)
class TurnoverFactors:
    minimum_reset: float
    clean_margin: float
    shortage_risk: float
    margin_minutes: float
    cart_utility: float
    resupply_cost: float
    wash_discard: float
    block_cover: float

    def __post_init__(self):
        if not all(isfinite(amount) for amount in (self.minimum_reset, self.clean_margin, self.shortage_risk, self.margin_minutes, self.cart_utility, self.resupply_cost, self.wash_discard, self.block_cover)):
            raise ValueError('门店班次存在无效的作业量测')

    def explain(self, labels=None):
        return (
            ('退房最低换套件', round(self.minimum_reset, 4)),
            ('基础布草减发后库存', round(self.clean_margin, 4)),
            ('到店前未覆盖份数', round(self.shortage_risk, 4)),
            ('距四小时洗回', round(self.margin_minutes, 4)),
            ('当前库存可开套数', round(self.cart_utility, 4)),
            ('每间库存周转需求', round(self.resupply_cost, 4)),
            ('近似剔除件数', round(self.wash_discard, 4)),
            ('团抵所需净布草', round(self.block_cover, 4)),
        )
