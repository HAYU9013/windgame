from collections import deque

from src.data_loader import SeasonalEventDefinition
from src.events import EventManager


def make_event(event_id: str, start: int, end: int, *, mana_rate: float = 1.0, rainfall: float = 0.0):
    return SeasonalEventDefinition(
        event_id=event_id,
        name=f"Event-{event_id}",
        description="Test event",
        start_month=start,
        end_month=end,
        first_year=1,
        rainfall_delta=rainfall,
        intensity_delta=0.1,
        southwest_delta=0.0,
        mana_cost_rate=mana_rate,
        satisfaction_delta=0.0,
        disaster_delta=0.0,
        news_on_start=(f"{event_id}-start",),
        news_on_end=(f"{event_id}-end",),
    )


def test_event_manager_initialization_announces_start_once():
    event = make_event("alpha", 1, 12)
    messages = deque()
    manager = EventManager([event])

    manager.initialize(1, 1, messages.append)
    manager.update(1, 1, messages.append)

    assert list(messages).count("alpha-start") == 1
    assert manager.list_active_events()[0].event_id == "alpha"


def test_event_manager_handles_end_and_modifiers():
    event = make_event("beta", 1, 3, mana_rate=0.8, rainfall=0.2)
    messages = []
    manager = EventManager([event])

    manager.initialize(2, 1, messages.append)
    modifiers = manager.aggregate_modifiers()
    assert modifiers.mana_cost_rate == 0.8
    assert modifiers.rainfall_bonus == 0.2

    manager.update(4, 1, messages.append)
    assert "beta-end" in messages
    assert manager.list_active_events() == []
