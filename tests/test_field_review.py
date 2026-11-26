from linenroute.pipeline import preview
from linenroute.laundry_transfer.service import operating_ledger


def note(key, measures, *, zone='甲区', state='已分派', estimate=0, hits=(), missing=()):
    return {'key':key,'zone':zone,'state':state,'estimate':estimate,'hits':hits,
            'unmeasured':missing,'measurements':dict(zip(('checked_out', 'on_hand', 'truck_eta', 'towel_issue', 'wash_reject', 'concert_rooms'),measures,strict=True))}


def test_field_plan_is_visible_and_references_real_tickets():
    desk = preview()
    plan = desk['sections'][6]
    assert plan['operating_title'] == '整笼调拨单'
    assert plan['operating_rows']
    scoped = {item['关联单据'] for item in plan['operating_rows'] if '关联单据' in item}
    assert scoped and scoped <= {row['key'] for row in desk['rows']}
    assert all(item['业务安排'] for item in plan['operating_rows'])


def test_donor_postings_clear_only_full_cages_and_never_self_transfer():
    store = note('LT-1',(10,240,70,0,0,0),zone='机场店')
    events = note('LT-2',(21,80,190,35,0,45),zone='会展店',estimate=89)
    overflow = note('LT-3',(30,110,190,35,0,25),zone='滨江店',estimate=210)
    decisions = operating_ledger([overflow,events,store])
    moved = [row for row in decisions if '计划件数' in row]
    assert moved and all(entry['计划件数']%12==0 for entry in moved)
    assert all(entry['发出门店']!=entry['接收门店'] for entry in moved)
    assert sum(entry['计划件数'] for entry in moved)<=212
    assert any(row['业务安排']=='等待洗房回告' for row in decisions)
