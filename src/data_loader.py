"""資料載入工具。"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple


@dataclass(slots=True)
class Region:
    region_id: str
    name: str
    population_weight: float
    agriculture_weight: float
    flood_threshold: float
    coordinates: tuple[int, int]


@dataclass(slots=True)
class Reservoir:
    reservoir_id: str
    name: str
    region_id: str
    capacity: float
    storage: float
    coordinates: tuple[int, int]


@dataclass(slots=True)
class Faction:
    faction_id: str
    name: str
    typhoon_holiday_preference: float
    flood_tolerance: float
    drought_tolerance: float


@dataclass(slots=True)
class SeasonalEventDefinition:
    event_id: str
    name: str
    description: str
    start_month: int
    end_month: int
    first_year: int
    rainfall_delta: float
    intensity_delta: float
    southwest_delta: float
    mana_cost_rate: float
    satisfaction_delta: float
    disaster_delta: float
    news_on_start: Tuple[str, ...]
    news_on_end: Tuple[str, ...]

    def is_month_active(self, month: int) -> bool:
        if self.start_month <= self.end_month:
            return self.start_month <= month <= self.end_month
        return month >= self.start_month or month <= self.end_month

    def is_available(self, year: int) -> bool:
        return year >= self.first_year


class DataRepository:
    """集中管理靜態資料。"""

    def __init__(self, base_path: Path | None = None) -> None:
        self.base_path = base_path or Path(__file__).resolve().parent.parent
        self._regions: list[Region] | None = None
        self._reservoirs: list[Reservoir] | None = None
        self._factions: list[Faction] | None = None
        self._events: list[SeasonalEventDefinition] | None = None

    def _load_json(self, relative_path: str) -> list[Dict[str, Any]]:
        file_path = self.base_path / "data" / relative_path
        with file_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    @property
    def regions(self) -> List[Region]:
        if self._regions is None:
            raw = self._load_json("regions.json")
            self._regions = [
                Region(
                    region_id=item["id"],
                    name=item["name"],
                    population_weight=float(item["population_weight"]),
                    agriculture_weight=float(item["agriculture_weight"]),
                    flood_threshold=float(item["flood_threshold"]),
                    coordinates=tuple(item["coordinates"]),
                )
                for item in raw
            ]
        return self._regions

    @property
    def reservoirs(self) -> List[Reservoir]:
        if self._reservoirs is None:
            raw = self._load_json("reservoirs.json")
            self._reservoirs = [
                Reservoir(
                    reservoir_id=item["id"],
                    name=item["name"],
                    region_id=item["region_id"],
                    capacity=float(item["capacity"]),
                    storage=float(item["storage"]),
                    coordinates=tuple(item["coordinates"]),
                )
                for item in raw
            ]
        return self._reservoirs

    @property
    def factions(self) -> List[Faction]:
        if self._factions is None:
            raw = self._load_json("factions.json")
            self._factions = [
                Faction(
                    faction_id=item["id"],
                    name=item["name"],
                    typhoon_holiday_preference=float(item["typhoon_holiday_preference"]),
                    flood_tolerance=float(item["flood_tolerance"]),
                    drought_tolerance=float(item["drought_tolerance"]),
                )
                for item in raw
            ]
        return self._factions

    @property
    def events(self) -> List[SeasonalEventDefinition]:
        if self._events is None:
            raw = self._load_json("events.json")
            self._events = [
                SeasonalEventDefinition(
                    event_id=item["id"],
                    name=item["name"],
                    description=item["description"],
                    start_month=int(item.get("start_month", 1)),
                    end_month=int(item.get("end_month", 12)),
                    first_year=int(item.get("first_year", 1)),
                    rainfall_delta=float(item.get("rainfall_delta", 0.0)),
                    intensity_delta=float(item.get("intensity_delta", 0.0)),
                    southwest_delta=float(item.get("southwest_delta", 0.0)),
                    mana_cost_rate=float(item.get("mana_cost_rate", 1.0)),
                    satisfaction_delta=float(item.get("satisfaction_delta", 0.0)),
                    disaster_delta=float(item.get("disaster_delta", 0.0)),
                    news_on_start=tuple(item.get("news_on_start", [])),
                    news_on_end=tuple(item.get("news_on_end", [])),
                )
                for item in raw
            ]
        return self._events
