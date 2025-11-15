from pathlib import Path

import pytest

from src.data_loader import DataRepository
from src.game_state import GameState, format_percentage, format_resource


def create_state() -> GameState:
    repo = DataRepository(base_path=Path(__file__).resolve().parent.parent)
    return GameState(repo)


def test_adjust_parameter_consumes_mana_and_generates_news():
    state = create_state()
    initial_mana = state.resources.mana

    state.adjust_parameter("intensity", 0.6)
    adjusted_mana = state.resources.mana
    expected_cost = 8.0 * abs(0.6 - 0.4)
    assert pytest.approx(initial_mana - expected_cost, rel=1e-6) == adjusted_mana

    state.step_simulation(1)
    assert any("颱風強度" in message for message in state.news)


def test_adjust_parameter_respects_mana_limit():
    state = create_state()
    state.resources.mana = 0.5
    before = state.weather.rainfall

    state.adjust_parameter("rainfall", 1.0)

    assert state.weather.rainfall == before
    assert state.resources.mana == 0.5


def test_step_simulation_updates_reservoirs_and_satisfaction():
    state = create_state()
    initial_storage = [res.storage for res in state.repository.reservoirs]

    state.step_simulation(6)

    updated_storage = [res.storage for res in state.repository.reservoirs]
    for before, after in zip(initial_storage, updated_storage):
        assert after >= before
    assert 0.0 <= state.satisfaction.overall <= 1.0


def test_event_news_triggered_after_advancing_months():
    state = create_state()
    state.step_simulation(720 * 4)

    assert any("梅雨鋒面" in message for message in state.news)


def test_change_time_scale_records_news():
    state = create_state()
    state.change_time_scale(2)
    state.step_simulation(1)

    assert state.time_scale == 2
    assert any("快轉" in message for message in state.news)


def test_positive_satisfaction_awards_resources():
    state = create_state()
    state.satisfaction.civil_support = 0.9
    state.satisfaction.education_support = 0.88
    state.satisfaction.agriculture_support = 0.9
    state.satisfaction.government_support = 0.87
    mana_before = state.resources.mana
    reputation_before = state.resources.reputation

    state._maybe_award_resources(6)

    assert state.resources.mana > mana_before
    assert state.resources.reputation > reputation_before


def test_format_helpers():
    assert format_percentage(0.753) == "75%"
    assert format_resource(12.345) == "12.3"


def test_spotlights_reflect_conditions():
    state = create_state()
    assert state.spotlights, "初始化時應至少提供一則焦點資訊"

    for reservoir in state.repository.reservoirs:
        reservoir.storage = reservoir.capacity * 0.2
    state._refresh_spotlights()
    titles = {title for title, _ in state.spotlights}
    assert "水情告急" in titles

    state.satisfaction.civil_support = 0.42
    state.satisfaction.agriculture_support = 0.41
    state.satisfaction.education_support = 0.76
    state.satisfaction.government_support = 0.74
    state._refresh_spotlights()
    titles = {title for title, _ in state.spotlights}
    assert "壓力焦點" in titles
    assert "民意加分" in titles
    assert any(title.endswith("態勢") for title in titles)
