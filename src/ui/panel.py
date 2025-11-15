"""資訊面板。"""
from __future__ import annotations

import pygame

from .. import config
from ..game_state import GameState, format_percentage, format_resource
from .components import Slider


class ControlPanel:
    def __init__(self, rect: pygame.Rect, game_state: GameState, font: pygame.font.Font, small_font: pygame.font.Font) -> None:
        self.rect = rect
        self.game_state = game_state
        self.font = font
        self.small_font = small_font
        self.sliders: list[Slider] = []
        self._create_sliders()

    def _create_sliders(self) -> None:
        slider_width = self.rect.width - 60
        base_x = self.rect.x + 30
        base_y = self.rect.y + 160
        spacing = 90
        self.sliders = [
            Slider(
                rect=pygame.Rect(base_x, base_y + idx * spacing, slider_width, 14),
                label=label,
                value=getattr(self.game_state.weather, key),
                on_change=lambda v, k=key: self.game_state.adjust_parameter(k, v),
            )
            for idx, (key, label) in enumerate(
                [
                    ("intensity", "颱風強度"),
                    ("rainfall", "降雨分布"),
                    ("path_bias", "路徑偏向"),
                    ("southwest_flow", "西南氣流"),
                ]
            )
        ]

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, config.COLOR_PANEL_BG, self.rect)
        title = self.font.render("神域控制台", True, config.COLOR_TEXT_PRIMARY)
        surface.blit(title, (self.rect.x + 30, self.rect.y + 24))
        self._draw_calendar(surface)
        self._draw_resources(surface)
        self._draw_satisfaction(surface)
        event_start_y = self._draw_spotlights(surface)
        self._draw_events(surface, event_start_y)
        for slider in self.sliders:
            slider.draw(surface, self.font, self.small_font)

    def handle_event(self, event: pygame.event.Event) -> None:
        for slider in self.sliders:
            slider.handle_event(event)

    def _draw_resources(self, surface: pygame.Surface) -> None:
        y = self.rect.y + 110
        lines = [
            ("神力", format_resource(self.game_state.resources.mana)),
            ("威望", format_resource(self.game_state.resources.reputation)),
            ("信仰點數", format_resource(self.game_state.resources.faith)),
            ("災損指標", format_resource(self.game_state.resources.disaster_debt)),
        ]
        for label, value in lines:
            text = self.font.render(f"{label}：{value}", True, config.COLOR_TEXT_SECONDARY)
            surface.blit(text, (self.rect.x + 30, y))
            y += 28

    def _draw_satisfaction(self, surface: pygame.Surface) -> None:
        y = self.rect.y + 320
        header = self.font.render("族群滿意度", True, config.COLOR_TEXT_PRIMARY)
        surface.blit(header, (self.rect.x + 30, y))
        y += 32
        bar_width = self.rect.width - 120
        entries = [
            ("上班族", self.game_state.satisfaction.civil_support),
            ("農業部門", self.game_state.satisfaction.agriculture_support),
            ("學生", self.game_state.satisfaction.education_support),
            ("政府", self.game_state.satisfaction.government_support),
        ]
        for label, value in entries:
            bar_rect = pygame.Rect(self.rect.x + 30, y + 20, bar_width, 12)
            pygame.draw.rect(surface, config.COLOR_PANEL_ACCENT, bar_rect, border_radius=4)
            fill_rect = pygame.Rect(bar_rect.x, bar_rect.y, int(bar_rect.width * value), bar_rect.height)
            pygame.draw.rect(surface, config.COLOR_STATUS_POSITIVE, fill_rect, border_radius=4)
            text = self.small_font.render(f"{label} {format_percentage(value)}", True, config.COLOR_TEXT_SECONDARY)
            surface.blit(text, (self.rect.x + 30, y))
            y += 50

    def _draw_calendar(self, surface: pygame.Surface) -> None:
        info = self.small_font.render(
            f"第{self.game_state.current_year}年 第{self.game_state.current_month}月｜{self.game_state.current_season}",
            True,
            config.COLOR_TEXT_SECONDARY,
        )
        surface.blit(info, (self.rect.x + 30, self.rect.y + 70))

    def _draw_events(self, surface: pygame.Surface, start_y: int) -> None:
        y = start_y
        header = self.font.render("當前事件", True, config.COLOR_TEXT_PRIMARY)
        surface.blit(header, (self.rect.x + 30, y))
        y += 30
        events = self.game_state.active_event_details
        if not events:
            text = self.small_font.render("目前無特殊事件。", True, config.COLOR_TEXT_SECONDARY)
            surface.blit(text, (self.rect.x + 30, y))
            return
        for name, description in events:
            summary = self._truncate(description, 16)
            text = self.small_font.render(f"• {name}：{summary}", True, config.COLOR_TEXT_SECONDARY)
            surface.blit(text, (self.rect.x + 30, y))
            y += 24

    def _draw_spotlights(self, surface: pygame.Surface) -> int:
        y = self.rect.y + 470
        header = self.font.render("島嶼脈動", True, config.COLOR_TEXT_PRIMARY)
        surface.blit(header, (self.rect.x + 30, y))
        y += 30
        entries = self.game_state.spotlights
        if not entries:
            text = self.small_font.render("尚無焦點動態。", True, config.COLOR_TEXT_SECONDARY)
            surface.blit(text, (self.rect.x + 30, y))
            return self.rect.y + 520

        for title, description in entries:
            title_text = self.small_font.render(f"• {title}", True, config.COLOR_TEXT_PRIMARY)
            surface.blit(title_text, (self.rect.x + 30, y))
            y += 20
            body_text = self.small_font.render(self._truncate(description, 24), True, config.COLOR_TEXT_SECONDARY)
            surface.blit(body_text, (self.rect.x + 46, y))
            y += 28

        return y + 10

    @staticmethod
    def _truncate(text: str, limit: int) -> str:
        return text if len(text) <= limit else text[:limit] + "…"
