"""Game state management and resource calculations."""
from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass
from typing import Deque, Iterable, Tuple

from .data_loader import DataRepository
from .events import EventManager, EventModifiers


@dataclass(slots=True)
class ResourceState:
    mana: float = 100.0
    reputation: float = 30.0
    faith: float = 20.0
    disaster_debt: float = 0.0


@dataclass(slots=True)
class WeatherParameters:
    intensity: float = 0.4
    rainfall: float = 0.5
    path_bias: float = 0.5
    southwest_flow: float = 0.3


@dataclass(slots=True)
class SatisfactionState:
    civil_support: float = 0.6
    agriculture_support: float = 0.6
    education_support: float = 0.6
    government_support: float = 0.6

    @property
    def overall(self) -> float:
        return (self.civil_support + self.agriculture_support + self.education_support + self.government_support) / 4


@dataclass(slots=True)
class SurvivalMetrics:
    public_support: float = 75.0
    water_security: float = 75.0
    infrastructure_integrity: float = 75.0
    divine_morale: float = 75.0

    def as_pairs(self) -> tuple[tuple[str, float], ...]:
        return (
            ("Public Support", self.public_support),
            ("Water Security", self.water_security),
            ("Infrastructure", self.infrastructure_integrity),
            ("Divine Morale", self.divine_morale),
        )


class GameState:
    """Coordinate the core gameplay logic."""

    def __init__(self, repository: DataRepository, rng: random.Random | None = None) -> None:
        self.repository = repository
        self.resources = ResourceState()
        self.weather = WeatherParameters()
        self.satisfaction = SatisfactionState()
        self.survival = SurvivalMetrics()
        self.time_scale = 1
        self._news: Deque[str] = deque(maxlen=6)
        self._pending_news: Deque[str] = deque()
        self._news_history: list[str] = []
        self._spotlights: list[tuple[str, str]] = []
        self.current_turn = 1
        self.elapsed_hours = 0.0
        self.total_real_seconds = 0.0
        self.game_over = False
        self.game_over_reason: str | None = None
        self._hours_since_event = 0.0
        self._rng = rng or random.Random()
        self.event_manager = EventManager(repository.events)
        self._event_modifiers = self.event_manager.aggregate_modifiers()
        self._init_default_news()
        self.event_manager.initialize(self.current_month, self.current_year, self.enqueue_news)
        self._event_modifiers = self.event_manager.aggregate_modifiers()
        self._refresh_spotlights()
        self._flush_news()

    def _init_default_news(self) -> None:
        defaults = [
            "Celestial bulletin: The new wind warden has taken office and citizens hope for stable weather.",
            "Central Weather Bureau: Warm seas this season are increasing the odds of typhoon formation.",
        ]
        self._news.extend(defaults)
        self._news_history.extend(defaults)

    # --- Public interface ---
    @property
    def news(self) -> Iterable[str]:
        return tuple(self._news)

    @property
    def current_month(self) -> int:
        total_months = int(self.elapsed_hours // 720)
        return total_months % 12 + 1

    @property
    def current_year(self) -> int:
        total_months = int(self.elapsed_hours // 720)
        return total_months // 12 + 1

    @property
    def current_season(self) -> str:
        month = self.current_month
        if month in (3, 4, 5):
            return "Spring"
        if month in (6, 7, 8):
            return "Summer"
        if month in (9, 10, 11):
            return "Autumn"
        return "Winter"

    @property
    def active_event_details(self) -> Tuple[Tuple[str, str], ...]:
        return tuple((event.name, event.description) for event in self.event_manager.list_active_events())

    @property
    def spotlights(self) -> Tuple[Tuple[str, str], ...]:
        return tuple(self._spotlights)

    @property
    def news_history(self) -> Tuple[str, ...]:
        return tuple(self._news_history)

    def enqueue_news(self, message: str) -> None:
        if message not in self._pending_news:
            self._pending_news.append(message)

    def adjust_parameter(self, key: str, target_value: float) -> None:
        target_value = max(0.0, min(1.0, target_value))
        before = getattr(self.weather, key)
        delta = abs(target_value - before)
        mana_multiplier = max(0.2, self._event_modifiers.mana_cost_rate)
        mana_cost = 8.0 * delta * mana_multiplier
        if mana_cost > self.resources.mana:
            return
        self.resources.mana -= mana_cost
        setattr(self.weather, key, target_value)
        self.enqueue_news(
            f"Celestial directive: {self._parameter_label(key)} adjusted to {target_value:.2f}, mana cost {mana_cost:.1f}."
        )

    def step_simulation(self, hours: float) -> None:
        if hours <= 0 or self.game_over:
            return
        self.elapsed_hours += hours
        self.total_real_seconds += hours * (5.0 / 24.0)
        self.event_manager.update(self.current_month, self.current_year, self.enqueue_news)
        self._event_modifiers = self.event_manager.aggregate_modifiers()
        self._update_reservoirs(hours)
        self._update_satisfaction()
        self._update_disaster_debt(hours)
        self._maybe_award_resources(hours)
        self._hours_since_event += hours
        self._decay_survival_metrics(hours)
        while self._hours_since_event >= 24.0:
            self._hours_since_event -= 24.0
            self._trigger_random_event()
        self._check_game_over()
        self._refresh_spotlights()
        self._flush_news()

    def change_time_scale(self, scale: int) -> None:
        self.time_scale = max(0, min(2, scale))
        labels = {0: "Pause", 1: "Normal", 2: "Fast"}
        self.enqueue_news(f"Time flow switched to {labels[self.time_scale]} mode.")

    def apply_response(self, action_id: str) -> None:
        if self.game_over:
            return
        action = self._response_catalog().get(action_id)
        if not action:
            return
        cost = action["cost"]
        if self.resources.mana < cost:
            self.enqueue_news("Insufficient mana to execute that divine response.")
            return
        self.resources.mana -= cost
        for metric, delta in action["effects"].items():
            self._shift_metric(metric, delta)
        self.enqueue_news(action["news"].format(cost=cost))
        self._check_game_over()

    # --- Internal logic ---
    def _update_reservoirs(self, hours: float) -> None:
        rainfall_factor, intensity_factor, southwest = self._effective_parameters()
        rainfall_effect = rainfall_factor * (0.5 + southwest * 0.8)
        intensity_effect = intensity_factor * 0.6 + 0.2
        inflow = rainfall_effect * intensity_effect * hours * 0.2
        drought_leak = max(0.1, 0.4 - rainfall_effect) * hours * 0.1
        for reservoir in self.repository.reservoirs:
            reservoir.storage = max(
                0.0, min(reservoir.capacity, reservoir.storage + inflow - drought_leak)
            )
            if reservoir.storage / reservoir.capacity > 0.9:
                self.enqueue_news(f"Water update: {reservoir.name} storage has exceeded 90%.")
            if reservoir.storage / reservoir.capacity < 0.3:
                self.enqueue_news(f"Water alert: {reservoir.name} storage is low and agriculture agencies are concerned.")

    def _update_satisfaction(self) -> None:
        rainfall_factor, intensity_factor, southwest = self._effective_parameters()
        flood_risk = intensity_factor * 0.6 + rainfall_factor * 0.4 + southwest * 0.3
        drought_relief = rainfall_factor * 0.7 + intensity_factor * 0.3
        typhoon_holiday_score = intensity_factor * 0.8 + rainfall_factor * 0.2

        shift = self._event_modifiers.satisfaction_shift

        self.satisfaction.civil_support = self._clamp01(
            0.5 + typhoon_holiday_score * 0.3 - flood_risk * 0.2 + shift
        )
        self.satisfaction.education_support = self._clamp01(
            0.45 + typhoon_holiday_score * 0.35 - flood_risk * 0.25 + shift
        )
        self.satisfaction.agriculture_support = self._clamp01(
            0.4 + drought_relief * 0.45 - flood_risk * 0.15 + shift
        )
        self.satisfaction.government_support = self._clamp01(
            0.55 + drought_relief * 0.2 - flood_risk * 0.25 + shift
        )

        if flood_risk > 0.75:
            self.enqueue_news("Disaster alert: Severe winds and rain may trigger flooding and landslides.")
        elif drought_relief < 0.35:
            self.enqueue_news("Agricultural water stress is rising; farmers are urging immediate rainfall support.")
        elif typhoon_holiday_score > 0.7:
            self.enqueue_news("Social buzz: Students across the island hope for typhoon days off.")

    def _update_disaster_debt(self, hours: float) -> None:
        rainfall_factor, intensity_factor, _ = self._effective_parameters()
        flood_pressure = max(0.0, intensity_factor * 0.7 + rainfall_factor * 0.5 - 0.6)
        drought_pressure = max(0.0, 0.5 - rainfall_factor)
        delta = (flood_pressure * 1.8 + drought_pressure * 0.8) * (hours / 6)
        delta *= max(0.0, 1.0 + self._event_modifiers.disaster_shift)
        self.resources.disaster_debt = max(0.0, self.resources.disaster_debt + delta - 0.05)
        if self.resources.disaster_debt > 10:
            self.enqueue_news("Celestial warning: The disaster index is high; reduce extreme adjustments.")

    def _maybe_award_resources(self, hours: float) -> None:
        overall = self.satisfaction.overall
        if overall > 0.65:
            reward = overall * 0.6 * (hours / 6)
            self.resources.reputation = min(100.0, self.resources.reputation + reward)
            self.resources.mana = min(120.0, self.resources.mana + reward * 1.5)
        if overall < 0.4:
            penalty = (0.4 - overall) * 1.2 * (hours / 6)
            self.resources.reputation = max(0.0, self.resources.reputation - penalty)
            self.enqueue_news("Poll numbers fall: Stakeholders are questioning the weather directives.")

    def _decay_survival_metrics(self, hours: float) -> None:
        morale_drain = max(0.4, 1.2 - self.resources.faith * 0.02)
        self._shift_metric("divine_morale", -hours * morale_drain * 0.3)

        satisfaction_gap = max(0.0, 0.6 - self.satisfaction.overall)
        self._shift_metric("public_support", -hours * (0.5 + satisfaction_gap * 3.0))

        average_fill = self._average_reservoir_fill()
        self._shift_metric("water_security", -hours * max(0.4, (0.7 - average_fill) * 4.5))

        disaster_pressure = 0.2 + self.resources.disaster_debt * 0.03
        self._shift_metric("infrastructure_integrity", -hours * disaster_pressure)

    def _trigger_random_event(self) -> None:
        events = self._daily_crisis_events()
        event = self._rng.choice(events)
        severity = self._rng.uniform(0.8, 1.2)
        messages = []
        for metric, impact in event["effects"].items():
            delta = impact * severity
            self._shift_metric(metric, delta)
            messages.append(f"{metric.replace('_', ' ').title()} {delta:+.0f}")
        detail = ", ".join(messages)
        self.enqueue_news(f"Crisis report: {event['description']} ({detail}).")

    def _shift_metric(self, metric: str, delta: float) -> None:
        current = getattr(self.survival, metric)
        updated = max(0.0, min(100.0, current + delta))
        setattr(self.survival, metric, updated)

    def _check_game_over(self) -> None:
        depleted = [
            name
            for name, value in self.survival.as_pairs()
            if value <= 0.0
        ]
        if depleted and not self.game_over:
            self.game_over = True
            exhausted = depleted[0]
            self.game_over_reason = f"{exhausted} collapsed."
            days_survived = self.survival_days
            self.enqueue_news(
                f"Game over: {self.game_over_reason} You endured {days_survived:.1f} days."
            )

    def _average_reservoir_fill(self) -> float:
        reservoirs = list(self.repository.reservoirs)
        if not reservoirs:
            return 0.0
        total_ratio = 0.0
        for reservoir in reservoirs:
            capacity = reservoir.capacity or 1.0
            total_ratio += max(0.0, min(1.0, reservoir.storage / capacity))
        return total_ratio / len(reservoirs)

    def _daily_crisis_events(self) -> tuple[dict[str, object], ...]:
        return (
            {
                "description": "Drought alerts shrink reservoir inflow",
                "effects": {"water_security": -self._rng.uniform(8, 16)},
            },
            {
                "description": "Public outcry over evacuation delays",
                "effects": {"public_support": -self._rng.uniform(10, 18)},
            },
            {
                "description": "Landslides disrupt regional transport",
                "effects": {
                    "infrastructure_integrity": -self._rng.uniform(9, 17),
                    "divine_morale": -self._rng.uniform(4, 10),
                },
            },
            {
                "description": "Long nights erode temple vigils",
                "effects": {"divine_morale": -self._rng.uniform(8, 14)},
            },
            {
                "description": "Power grid strain triggers rolling blackouts",
                "effects": {
                    "infrastructure_integrity": -self._rng.uniform(11, 19),
                    "public_support": -self._rng.uniform(4, 9),
                },
            },
        )

    def _response_catalog(self) -> dict[str, dict[str, object]]:
        return {
            "campaign": {
                "cost": 12.0,
                "effects": {"public_support": 14.0, "divine_morale": 6.0},
                "news": "Mobilized outreach restored public confidence at the cost of {cost:.0f} mana.",
            },
            "rain_ritual": {
                "cost": 10.0,
                "effects": {"water_security": 16.0},
                "news": "A rain ritual replenished reservoirs after spending {cost:.0f} mana.",
            },
            "reinforce_grid": {
                "cost": 14.0,
                "effects": {"infrastructure_integrity": 18.0},
                "news": "Divine reinforcement stabilized the grid using {cost:.0f} mana.",
            },
            "renew_prayers": {
                "cost": 8.0,
                "effects": {"divine_morale": 18.0},
                "news": "Renewed prayers rekindled morale for {cost:.0f} mana.",
            },
        }

    def _flush_news(self) -> None:
        while self._pending_news:
            message = self._pending_news.popleft()
            self._news.append(message)
            self._news_history.append(message)

    def _refresh_spotlights(self) -> None:
        spotlights: list[tuple[str, str]] = []

        reservoirs = list(self.repository.reservoirs)
        if reservoirs:
            key_ratio = lambda res: (res.storage / res.capacity) if res.capacity else 0.0
            richest = max(reservoirs, key=key_ratio)
            driest = min(reservoirs, key=key_ratio)
            richest_ratio = key_ratio(richest)
            driest_ratio = key_ratio(driest)

            if driest_ratio < 0.35:
                spotlights.append(
                    (
                        "Water Supply Alert",
                        f"{driest.name} is at just {int(driest_ratio * 100)}% capacity, prompting local conservation campaigns.",
                    )
                )
            else:
                spotlights.append(
                    (
                        "Water Supply Highlight",
                        f"{richest.name} has reached {int(richest_ratio * 100)}% storage, easing pressure on distribution teams.",
                    )
                )

        satisfaction_entries = [
            ("Office Workers", self.satisfaction.civil_support),
            ("Agriculture Sector", self.satisfaction.agriculture_support),
            ("Students", self.satisfaction.education_support),
            ("Government", self.satisfaction.government_support),
        ]
        if satisfaction_entries:
            happiest = max(satisfaction_entries, key=lambda item: item[1])
            most_concerned = min(satisfaction_entries, key=lambda item: item[1])

            if happiest[1] >= 0.7:
                spotlights.append(
                    (
                        "Public Approval Boost",
                        f"{happiest[0]} report satisfaction of {int(happiest[1] * 100)}%, and conversations are largely positive.",
                    )
                )
            if most_concerned[1] <= 0.45:
                spotlights.append(
                    (
                        "Pressure Spotlight",
                        f"{most_concerned[0]} are down to {int(most_concerned[1] * 100)}% satisfaction, watch for policy fallout.",
                    )
                )
        rainfall, intensity, southwest = self._effective_parameters()
        climate_message = (
            f"Rainfall index {int(rainfall * 100)}%, wind strength {int(intensity * 100)}%, "
            f"southwest flow {int(southwest * 100)}% define this season's climate."
        )
        spotlights.append((f"{self.current_season} Outlook", climate_message))

        self._spotlights = spotlights[:4]

    @staticmethod
    def _clamp01(value: float) -> float:
        return max(0.0, min(1.0, value))

    @staticmethod
    def _parameter_label(key: str) -> str:
        mapping = {
            "intensity": "Typhoon Intensity",
            "rainfall": "Rainfall Distribution",
            "path_bias": "Path Bias",
            "southwest_flow": "Southwest Flow",
        }
        return mapping.get(key, key)

    def _effective_parameters(self) -> Tuple[float, float, float]:
        rainfall = self._clamp01(self.weather.rainfall + self._event_modifiers.rainfall_bonus)
        intensity = self._clamp01(self.weather.intensity + self._event_modifiers.intensity_bonus)
        southwest = self._clamp01(self.weather.southwest_flow + self._event_modifiers.southwest_bonus)
        return rainfall, intensity, southwest

    @property
    def survival_days(self) -> float:
        return self.elapsed_hours / 24.0

    @property
    def survival_seconds(self) -> float:
        return self.total_real_seconds

    @property
    def survival_summary(self) -> str:
        if not self.game_over_reason:
            return ""
        return f"{self.game_over_reason} You lasted {self.survival_days:.1f} days."


def format_percentage(value: float) -> str:
    return f"{int(value * 100):d}%"


def format_resource(value: float) -> str:
    return f"{value:.1f}"
