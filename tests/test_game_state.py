from pathlib import Path
import random

import pytest

from src.data_loader import DataRepository
from src.game_state import GameState, format_percentage, format_resource


def create_state() -> GameState:
    repo = DataRepository(base_path=Path(__file__).resolve().parent.parent)
    return GameState(repo, rng=random.Random(0))


def test_adjust_parameter_consumes_mana_and_generates_news():
    state = create_state()
    initial_mana = state.resources.mana

    state.adjust_parameter("intensity", 0.6)
    adjusted_mana = state.resources.mana
    expected_cost = 8.0 * abs(0.6 - 0.4)
    assert pytest.approx(initial_mana - expected_cost, rel=1e-6) == adjusted_mana

    state.step_simulation(1)
    assert any("Typhoon Intensity" in message for message in state.news)


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

    assert any("Meiyu front" in message for message in state.news_history)


def test_change_time_scale_records_news():
    state = create_state()
    state.change_time_scale(2)
    state.step_simulation(1)

    assert state.time_scale == 2
    assert any("Fast mode" in message for message in state.news)


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
    assert state.spotlights, "Expected at least one spotlight during initialization"

    for reservoir in state.repository.reservoirs:
        reservoir.storage = reservoir.capacity * 0.2
    state._refresh_spotlights()
    titles = {title for title, _ in state.spotlights}
    assert "Water Supply Alert" in titles

    state.satisfaction.civil_support = 0.42
    state.satisfaction.agriculture_support = 0.41
    state.satisfaction.education_support = 0.76
    state.satisfaction.government_support = 0.74
    state._refresh_spotlights()
    titles = {title for title, _ in state.spotlights}
    assert "Pressure Spotlight" in titles
    assert "Public Approval Boost" in titles
    assert any(title.endswith("Outlook") for title in titles)


def test_survival_metrics_decay_and_response():
    state = create_state()
    initial_support = state.survival.public_support

    state.step_simulation(12)

    assert state.survival.public_support < initial_support

    mana_before = state.resources.mana
    state.apply_response("campaign")

    assert state.resources.mana < mana_before
    assert state.survival.public_support > initial_support


def test_game_over_when_metric_depleted():
    state = create_state()
    state.survival.public_support = 0.2

    state.step_simulation(1)

    assert state.game_over
    assert state.game_over_reason is not None
    assert "Public Support" in state.game_over_reason
    assert state.survival_summary
