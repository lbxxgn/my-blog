"""utils.timezone 单元测试（UTC 存储 -> 本地 UTC+8 展示）。"""
from datetime import datetime, timedelta

from utils.timezone import (
    LOCAL_OFFSET,
    local_now,
    to_local,
    utc_now,
    utc_to_local,
)


class TestUtcToLocal:
    def test_naive_utc_string(self):
        assert utc_to_local('2026-06-30 03:02:38') == '2026-06-30 11:02:38'

    def test_iso_string_with_t(self):
        assert utc_to_local('2026-06-30T03:02:38') == '2026-06-30 11:02:38'

    def test_aware_utc_string(self):
        assert utc_to_local('2026-06-30T03:02:38+00:00') == '2026-06-30 11:02:38'

    def test_naive_datetime_treated_as_utc(self):
        assert utc_to_local(datetime(2026, 6, 30, 3, 2, 38)) == '2026-06-30 11:02:38'

    def test_date_boundary_crosses_midnight(self):
        # 本地 00:30 的前一天 16:30（UTC）应换算回次日
        assert utc_to_local('2026-06-29 16:30:00') == '2026-06-30 00:30:00'

    def test_custom_format(self):
        assert utc_to_local('2026-06-30 03:02:38', fmt='%Y-%m-%d') == '2026-06-30'

    def test_empty_and_none(self):
        assert utc_to_local('') == ''
        assert utc_to_local(None) == ''

    def test_invalid_string_returned_as_is(self):
        assert utc_to_local('not-a-date') == 'not-a-date'


class TestNowHelpers:
    def test_offset_is_eight_hours(self):
        assert LOCAL_OFFSET == timedelta(hours=8)

    def test_local_now_is_utc_plus_offset(self):
        diff = local_now() - utc_now()
        # 允许执行耗时造成的秒级误差
        assert timedelta(hours=7, minutes=59, seconds=59) < diff < timedelta(hours=8, seconds=5)

    def test_to_local(self):
        assert to_local(datetime(2026, 1, 1, 0, 0, 0)) == datetime(2026, 1, 1, 8, 0, 0)
