"""Yahoo Finance 価格取得のテスト（モック使用）。"""

from datetime import datetime, timezone
from unittest.mock import patch

from src import yahoo

# timestamp: 2026-10-22 / 2026-10-23 (UTC)
TS = [int(datetime(2026, 10, d, tzinfo=timezone.utc).timestamp()) for d in (22, 23)]


def _chart_body(closes, volumes=None):
    return {
        "chart": {
            "result": [{
                "timestamp": TS[:len(closes)],
                "indicators": {"quote": [{"close": closes, "volume": volumes}]},
            }],
        },
    }


def test_parse_chart_calculates_change_pct():
    # close 配列の最後の2点から (P_n/P_{n-1}-1)*100 で自前計算する
    parsed = yahoo.parse_chart(_chart_body([3630.0, 3650.0], [1000, 1200]))
    assert parsed["close"] == 3650.0
    assert abs(parsed["change_pct"] - round((3650.0 / 3630.0 - 1) * 100, 3)) < 1e-9
    assert parsed["volume"] == 1200  # close と同じ最終ポイントの出来高
    assert parsed["as_of"] == "2026-10-23"


def test_parse_chart_volume_fallback_and_missing():
    # 最終点の volume が None の場合は直近の有効値にフォールバック
    parsed = yahoo.parse_chart(_chart_body([3630.0, 3650.0], [1000, None]))
    assert parsed["volume"] == 1000
    # volume 配列自体がない場合は None
    parsed = yahoo.parse_chart(_chart_body([3630.0, 3650.0]))
    assert parsed["volume"] is None


def test_parse_chart_single_point_no_change():
    parsed = yahoo.parse_chart(_chart_body([3650.0]))
    assert parsed["close"] == 3650.0
    assert parsed["change_pct"] is None


def test_parse_chart_no_data():
    assert yahoo.parse_chart({"chart": {"result": []}}) is None
    assert yahoo.parse_chart(_chart_body([None, None])) is None


def _chart_body_n(n, closes, volumes):
    from datetime import timedelta
    base = datetime(2026, 9, 1, tzinfo=timezone.utc)
    ts = [int((base + timedelta(days=i)).timestamp()) for i in range(n)]
    return {
        "chart": {
            "result": [{
                "timestamp": ts,
                "indicators": {"quote": [{"close": closes, "volume": volumes}]},
            }],
        },
    }


def test_parse_chart_avg_volume_and_rvol():
    # 正常系: 当日を含まない直前20営業日の平均、当日出来高/volume で rvol
    closes = [3000.0] * 21 + [3100.0]
    volumes = [10000] * 21 + [25000]  # 直前21点のうち当日を除く直前20点=10000
    parsed = yahoo.parse_chart(_chart_body_n(22, closes, volumes))
    assert parsed["avg_volume_20d"] == 10000
    assert parsed["rvol"] == 2.5
    assert parsed["volume"] == 25000


def test_parse_chart_avg_volume_ignores_null_volumes():
    # 出来高 null の日は除外して平均する（直前21点中19点有効 → その平均）
    closes = [3000.0] * 22
    volumes = [10000] * 19 + [None, None] + [25000]
    parsed = yahoo.parse_chart(_chart_body_n(22, closes, volumes))
    assert parsed["avg_volume_20d"] == 10000
    assert parsed["rvol"] == 2.5


def test_parse_chart_avg_volume_needs_10_days():
    # 直前の有効な出来高が10営業日分未満なら avg_volume_20d=None（上場直後など）
    closes = [3000.0] * 10
    volumes = [None] * 8 + [10000] + [25000]
    parsed = yahoo.parse_chart(_chart_body_n(10, closes, volumes))
    assert parsed["avg_volume_20d"] is None
    assert parsed["rvol"] is None


def test_parse_chart_rvol_null_when_volume_null():
    # 当日出来高が null の場合は直近の有効値にフォールバック（既存挙動）し、その値で rvol を算出
    closes = [3000.0] * 22
    volumes = [10000] * 21 + [None]
    parsed = yahoo.parse_chart(_chart_body_n(22, closes, volumes))
    assert parsed["avg_volume_20d"] == 10000
    assert parsed["volume"] == 10000
    assert parsed["rvol"] == 1.0
    # 全点の出来高が null なら volume=None、rvol も null
    parsed = yahoo.parse_chart(_chart_body_n(22, closes, [None] * 22))
    assert parsed["avg_volume_20d"] is None
    assert parsed["volume"] is None
    assert parsed["rvol"] is None


def test_parse_chart_excludes_current_day_from_average():
    # 平均に当日を含めないこと: 直前20点=10000、当日=100000 でも平均は10000
    closes = [3000.0] * 21 + [3100.0]
    volumes = [10000] * 21 + [100000]
    parsed = yahoo.parse_chart(_chart_body_n(22, closes, volumes))
    assert parsed["avg_volume_20d"] == 10000
    assert parsed["rvol"] == 10.0


def test_symbol():
    assert yahoo.symbol("1306") == "1306.T"


@patch("src.yahoo._fetch_one")
def test_fetch_prices_skips_failures(mock_fetch):
    # 取得失敗した銘柄は戻り値に含めず「データなし」扱いにする
    mock_fetch.side_effect = [
        {"close": 3650.0, "change_pct": 0.5, "volume": 1200, "as_of": "2026-10-23"},
        None,
    ]
    out = yahoo.fetch_prices(["1305", "9999"])
    assert out == {"1305": {"close": 3650.0, "change_pct": 0.5, "volume": 1200, "as_of": "2026-10-23"}}


@patch("src.yahoo._fetch_one")
def test_fetch_prices_respects_exclude(mock_fetch):
    yahoo.YAHOO_EXCLUDE.add("9999")
    try:
        out = yahoo.fetch_prices(["9999"])
        assert out == {}
        mock_fetch.assert_not_called()
    finally:
        yahoo.YAHOO_EXCLUDE.discard("9999")
