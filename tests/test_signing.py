"""Pure-function tests."""

from custom_components.zte_kids.api import ZteKidsClient
from custom_components.zte_kids.coordinator import location_fix_epoch


def test_location_fix_epoch_ms_and_s() -> None:
    assert location_fix_epoch({"lastLocation": {"timestamp": 1_700_000_000_000}}) == 1_700_000_000
    assert location_fix_epoch({"lastLocation": {"timestamp": 1_700_000_000}}) == 1_700_000_000
    assert location_fix_epoch({"lastLocation": {"timestamp": ""}}) is None
    assert location_fix_epoch({}) is None


def test_devices_by_imei_merges_groups() -> None:
    out = ZteKidsClient.devices_by_imei(
        {"ownedDevices": [{"imei": " 1 "}], "chatGroupDevices": [{"imei": "2"}, {}]}
    )
    assert set(out) == {"1", "2"}
