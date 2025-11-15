"""Management for seasonal and special events."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Tuple

from .data_loader import SeasonalEventDefinition


@dataclass(slots=True)
class EventModifiers:
    rainfall_bonus: float = 0.0
    intensity_bonus: float = 0.0
    southwest_bonus: float = 0.0
    mana_cost_rate: float = 1.0
    satisfaction_shift: float = 0.0
    disaster_shift: float = 0.0

    def apply(self, event: SeasonalEventDefinition) -> None:
        self.rainfall_bonus += event.rainfall_delta
        self.intensity_bonus += event.intensity_delta
        self.southwest_bonus += event.southwest_delta
        self.mana_cost_rate *= event.mana_cost_rate
        self.satisfaction_shift += event.satisfaction_delta
        self.disaster_shift += event.disaster_delta


class EventManager:
    """Handle activation and management of seasonal and special events."""

    def __init__(self, events: Iterable[SeasonalEventDefinition]) -> None:
        self._events = list(events)
        self._active: Dict[str, Tuple[SeasonalEventDefinition, int]] = {}
        self._announced_start: set[Tuple[str, int]] = set()
        self._announced_end: set[Tuple[str, int]] = set()

    def initialize(self, current_month: int, current_year: int, enqueue_news: Callable[[str], None]) -> None:
        self._active.clear()
        self._announced_start.clear()
        self._announced_end.clear()
        self.update(current_month, current_year, enqueue_news)

    def update(self, current_month: int, current_year: int, enqueue_news: Callable[[str], None]) -> None:
        active_now: Dict[str, Tuple[SeasonalEventDefinition, int]] = {}
        for event in self._events:
            if not event.is_available(current_year):
                continue
            if event.is_month_active(current_month):
                start_year = current_year
                if event.event_id in self._active:
                    start_year = self._active[event.event_id][1]
                active_now[event.event_id] = (event, start_year)
                start_key = (event.event_id, start_year)
                if start_key not in self._announced_start:
                    for message in event.news_on_start:
                        enqueue_news(message)
                    self._announced_start.add(start_key)
        ended_ids = [event_id for event_id in self._active if event_id not in active_now]
        for event_id in ended_ids:
            event, start_year = self._active[event_id]
            end_key = (event_id, start_year)
            if end_key not in self._announced_end:
                for message in event.news_on_end:
                    enqueue_news(message)
                self._announced_end.add(end_key)
        self._active = active_now

    def aggregate_modifiers(self) -> EventModifiers:
        modifiers = EventModifiers()
        for event, _ in self._active.values():
            modifiers.apply(event)
        return modifiers

    def list_active_events(self) -> List[SeasonalEventDefinition]:
        return [event for event, _ in self._active.values()]
