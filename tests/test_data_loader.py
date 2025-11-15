from pathlib import Path

from src.data_loader import (
    DataRepository,
    SeasonalEventDefinition,
)


def test_repository_caches_loaded_regions(tmp_path):
    repo = DataRepository(base_path=Path(__file__).resolve().parent.parent)

    first = repo.regions
    second = repo.regions

    assert first is second
    assert len(first) >= 1
    assert all(hasattr(region, "name") for region in first)


def test_seasonal_event_wraparound_month_active():
    event = SeasonalEventDefinition(
        event_id="test",
        name="跨年事件",
        description="測試月份跨越年度",
        start_month=11,
        end_month=2,
        first_year=1,
        rainfall_delta=0.0,
        intensity_delta=0.0,
        southwest_delta=0.0,
        mana_cost_rate=1.0,
        satisfaction_delta=0.0,
        disaster_delta=0.0,
        news_on_start=("start",),
        news_on_end=("end",),
    )

    active_months = {month for month in range(1, 13) if event.is_month_active(month)}

    assert active_months == {11, 12, 1, 2}
    assert event.is_available(1)
    assert not event.is_available(0)
