"""遊戲狀態與資源運算。"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Iterable, Tuple

from .data_loader import DataRepository, Faction, Region, Reservoir
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


class GameState:
    """集中處理遊戲內部邏輯。"""

    def __init__(self, repository: DataRepository) -> None:
        self.repository = repository
        self.resources = ResourceState()
        self.weather = WeatherParameters()
        self.satisfaction = SatisfactionState()
        self.time_scale = 1
        self._news: Deque[str] = deque(maxlen=6)
        self._pending_news: Deque[str] = deque()
        self._spotlights: list[tuple[str, str]] = []
        self.current_turn = 1
        self.elapsed_hours = 0.0
        self.event_manager = EventManager(repository.events)
        self._event_modifiers = self.event_manager.aggregate_modifiers()
        self._init_default_news()
        self.event_manager.initialize(self.current_month, self.current_year, self.enqueue_news)
        self._event_modifiers = self.event_manager.aggregate_modifiers()
        self._refresh_spotlights()
        self._flush_news()

    def _init_default_news(self) -> None:
        self._news.extend([
            "天界播報：新任風巡者就任，民眾期待穩定氣候。",
            "中央氣象署：本季海溫偏高，颱風生成機率增加。",
        ])

    # --- 公用介面 ---
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
            return "春季"
        if month in (6, 7, 8):
            return "夏季"
        if month in (9, 10, 11):
            return "秋季"
        return "冬季"

    @property
    def active_event_details(self) -> Tuple[Tuple[str, str], ...]:
        return tuple((event.name, event.description) for event in self.event_manager.list_active_events())

    @property
    def spotlights(self) -> Tuple[Tuple[str, str], ...]:
        return tuple(self._spotlights)

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
        self.enqueue_news(f"天界調度：{self._parameter_label(key)}調整至 {target_value:.2f}，消耗神力 {mana_cost:.1f} 點。")

    def step_simulation(self, hours: float) -> None:
        if hours <= 0:
            return
        self.elapsed_hours += hours
        self.event_manager.update(self.current_month, self.current_year, self.enqueue_news)
        self._event_modifiers = self.event_manager.aggregate_modifiers()
        self._update_reservoirs(hours)
        self._update_satisfaction()
        self._update_disaster_debt(hours)
        self._maybe_award_resources(hours)
        self._refresh_spotlights()
        self._flush_news()

    def change_time_scale(self, scale: int) -> None:
        self.time_scale = max(0, min(2, scale))
        labels = {0: "暫停", 1: "正常", 2: "快轉"}
        self.enqueue_news(f"時間流速切換為{labels[self.time_scale]}模式。")

    # --- 內部邏輯 ---
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
                self.enqueue_news(f"水情快訊：{reservoir.name} 蓄水率突破 90%。")
            if reservoir.storage / reservoir.capacity < 0.3:
                self.enqueue_news(f"水情告急：{reservoir.name} 蓄水偏低，農業單位示警。")

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
            self.enqueue_news("災害警戒：強風豪雨可能引發淹水與土石流。")
        elif drought_relief < 0.35:
            self.enqueue_news("農業用水壓力增加，農民呼籲儘速補雨。")
        elif typhoon_holiday_score > 0.7:
            self.enqueue_news("社群熱議：各地學生期待放颱風假。")

    def _update_disaster_debt(self, hours: float) -> None:
        rainfall_factor, intensity_factor, _ = self._effective_parameters()
        flood_pressure = max(0.0, intensity_factor * 0.7 + rainfall_factor * 0.5 - 0.6)
        drought_pressure = max(0.0, 0.5 - rainfall_factor)
        delta = (flood_pressure * 1.8 + drought_pressure * 0.8) * (hours / 6)
        delta *= max(0.0, 1.0 + self._event_modifiers.disaster_shift)
        self.resources.disaster_debt = max(0.0, self.resources.disaster_debt + delta - 0.05)
        if self.resources.disaster_debt > 10:
            self.enqueue_news("天界示警：災損指標偏高，請降低極端操作。")

    def _maybe_award_resources(self, hours: float) -> None:
        overall = self.satisfaction.overall
        if overall > 0.65:
            reward = overall * 0.6 * (hours / 6)
            self.resources.reputation = min(100.0, self.resources.reputation + reward)
            self.resources.mana = min(120.0, self.resources.mana + reward * 1.5)
        if overall < 0.4:
            penalty = (0.4 - overall) * 1.2 * (hours / 6)
            self.resources.reputation = max(0.0, self.resources.reputation - penalty)
            self.enqueue_news("民調下滑：各界對天氣調度產生疑慮。")

    def _flush_news(self) -> None:
        while self._pending_news:
            message = self._pending_news.popleft()
            self._news.append(message)

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
                spotlights.append(("水情告急", f"{driest.name} 目前僅有 {int(driest_ratio * 100)}% 的蓄水，地方政府啟動節水宣導。"))
            else:
                spotlights.append(("水情亮點", f"{richest.name} 蓄水率達 {int(richest_ratio * 100)}%，供水團隊回報壓力明顯下降。"))

        satisfaction_entries = [
            ("上班族", self.satisfaction.civil_support),
            ("農業部門", self.satisfaction.agriculture_support),
            ("學生", self.satisfaction.education_support),
            ("政府", self.satisfaction.government_support),
        ]
        if satisfaction_entries:
            happiest = max(satisfaction_entries, key=lambda item: item[1])
            most_concerned = min(satisfaction_entries, key=lambda item: item[1])

            if happiest[1] >= 0.7:
                spotlights.append(("民意加分", f"{happiest[0]} 對本輪調度滿意度達 {int(happiest[1] * 100)}%，社群討論偏向正面。"))
            if most_concerned[1] <= 0.45:
                spotlights.append(("壓力焦點", f"{most_concerned[0]} 僅剩 {int(most_concerned[1] * 100)}% 滿意度，需留意後續政策調整。"))
        rainfall, intensity, southwest = self._effective_parameters()
        climate_message = f"降雨指數 {int(rainfall * 100)}%，風勢 {int(intensity * 100)}%，西南氣流 {int(southwest * 100)}%，構成本季主流氣候。"
        spotlights.append((f"{self.current_season}態勢", climate_message))

        self._spotlights = spotlights[:4]

    @staticmethod
    def _clamp01(value: float) -> float:
        return max(0.0, min(1.0, value))

    @staticmethod
    def _parameter_label(key: str) -> str:
        mapping = {
            "intensity": "颱風強度",
            "rainfall": "降雨分布",
            "path_bias": "路徑偏向",
            "southwest_flow": "西南氣流",
        }
        return mapping.get(key, key)

    def _effective_parameters(self) -> Tuple[float, float, float]:
        rainfall = self._clamp01(self.weather.rainfall + self._event_modifiers.rainfall_bonus)
        intensity = self._clamp01(self.weather.intensity + self._event_modifiers.intensity_bonus)
        southwest = self._clamp01(self.weather.southwest_flow + self._event_modifiers.southwest_bonus)
        return rainfall, intensity, southwest


def format_percentage(value: float) -> str:
    return f"{int(value * 100):d}%"


def format_resource(value: float) -> str:
    return f"{value:.1f}"
