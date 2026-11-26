from collections.abc import Mapping
from decimal import Decimal

from .contracts import MeasureIssue


from dataclasses import dataclass


def form_number(form, sheet, name, minimum, maximum):
    from .service import number

    table = form.get(sheet)
    if not isinstance(table, Mapping):
        raise MeasureIssue(sheet, 'FORM_SECTION_REQUIRED')
    return Decimal(str(number(table.get(name), name, minimum, maximum)))


@dataclass(frozen=True, slots=True)
class LinenCagesSheet:
    checked_rooms: Decimal
    available_pieces: Decimal
    truck_arrival_sec: Decimal
    reserved_towels: Decimal
    reject_basis_points: Decimal
    blocked_group_rooms: Decimal

    def fields(self):
        return {
            'checked_out': float(self.checked_rooms),
            'on_hand': float(self.available_pieces),
            'truck_eta': float(self.truck_arrival_sec) / 60,
            'towel_issue': float(self.reserved_towels),
            'wash_reject': float(self.reject_basis_points) / 100,
            'concert_rooms': float(self.blocked_group_rooms),
        }

    def validation(self):
        fields = self.fields()
        checked_out = fields['checked_out']
        on_hand = fields['on_hand']
        truck_eta = fields['truck_eta']
        towel_issue = fields['towel_issue']
        wash_reject = fields['wash_reject']
        concert_rooms = fields['concert_rooms']
        minimum_supply = checked_out*2+towel_issue
        clean_duty = on_hand*(1-wash_reject/100)
        group_buffer = 2*concert_rooms
        haul_gap = minimum_supply+group_buffer-clean_duty
        alerts = []
        if clean_duty<minimum_supply*.1 and truck_eta>=190:
            alerts.append(('available_pieces', 'WAREHOUSE_COUNT_VERIFY'))
        if towel_issue>checked_out*10:
            alerts.append(('reserved_towels', 'TOWEL_RELEASE_DOUBLE_CHECK'))
        if haul_gap>530:
            alerts.append(('blocked_group_rooms', 'CHECK_GROUP_BLOCK_TOTAL'))
        return tuple(alerts)


def read_linen_cages(form):
    return LinenCagesSheet(
        checked_rooms=form_number(form, '退房交接', 'checked_rooms', 8, 180),
        available_pieces=form_number(form, '退房交接', 'available_pieces', 0, 480),
        truck_arrival_sec=form_number(form, '净成品入笼', 'truck_arrival_sec', 900, 14400),
        reserved_towels=form_number(form, '净成品入笼', 'reserved_towels', 0, 155),
        reject_basis_points=form_number(form, '洗涤派车', 'reject_basis_points', 0, 2300),
        blocked_group_rooms=form_number(form, '洗涤派车', 'blocked_group_rooms', 0, 110),
    )


def explicit_rows(form):
    if not isinstance(form, Mapping):
        raise MeasureIssue('form', 'FORM_OBJECT_REQUIRED')
    note = read_linen_cages(form)
    return note.fields(), note.validation()


def check_native_history(source):
    if not isinstance(source, Mapping) or 'form' not in source:
        return source
    if any(key in source for key in ('checked_out', 'on_hand', 'truck_eta', 'towel_issue', 'wash_reject', 'concert_rooms')):
        raise MeasureIssue('form','MIXED_FORM_AND_FLAT_READING')
    converted, flags = explicit_rows(source['form'])
    if flags:
        raise MeasureIssue(*flags[0])
    return {**source, **converted}
