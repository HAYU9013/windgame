"""Information panel rendering."""
from __future__ import annotations

import pygame

from .. import config
from ..game_state import GameState, format_percentage, format_resource
from .components import Button, Slider


class ControlPanel:
    def __init__(self, rect: pygame.Rect, game_state: GameState, font: pygame.font.Font, small_font: pygame.font.Font) -> None:
        self.rect = rect
        self.game_state = game_state
        self.font = font
        self.small_font = small_font
        self.sliders: list[Slider] = []
        self.response_buttons: list[Button] = []
        self._create_sliders()
        self._create_response_buttons()

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
                    ("intensity", "Typhoon Intensity"),
                    ("rainfall", "Rainfall Distribution"),
                    ("path_bias", "Path Bias"),
                    ("southwest_flow", "Southwest Flow"),
                ]
            )
        ]

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, config.COLOR_PANEL_BG, self.rect)
        title = self.font.render("Divine Control Panel", True, config.COLOR_TEXT_PRIMARY)
        surface.blit(title, (self.rect.x + 30, self.rect.y + 24))
        self._draw_calendar(surface)
        self._draw_resources(surface)
        self._draw_survival_metrics(surface)
        self._draw_satisfaction(surface)
        event_start_y = self._draw_spotlights(surface)
        self._draw_events(surface, event_start_y)
        for slider in self.sliders:
            slider.draw(surface, self.font, self.small_font)
        for button in self.response_buttons:
            button.draw(surface, self.font)

    def handle_event(self, event: pygame.event.Event) -> None:
        for slider in self.sliders:
            slider.handle_event(event)
        for button in self.response_buttons:
            button.handle_event(event)

    def _draw_resources(self, surface: pygame.Surface) -> None:
        y = self.rect.y + 110
        lines = [
            ("Mana", format_resource(self.game_state.resources.mana)),
            ("Reputation", format_resource(self.game_state.resources.reputation)),
            ("Faith", format_resource(self.game_state.resources.faith)),
            ("Disaster Index", format_resource(self.game_state.resources.disaster_debt)),
        ]
        for label, value in lines:
            text = self.font.render(f"{label}: {value}", True, config.COLOR_TEXT_SECONDARY)
            surface.blit(text, (self.rect.x + 30, y))
            y += 28

    def _draw_survival_metrics(self, surface: pygame.Surface) -> None:
        y = self.rect.y + 210
        header = self.font.render("Stability Metrics", True, config.COLOR_TEXT_PRIMARY)
        surface.blit(header, (self.rect.x + 30, y))
        y += 32
        bar_width = self.rect.width - 120
        for label, value in self.game_state.survival.as_pairs():
            ratio = max(0.0, min(1.0, value / 100.0))
            bar_rect = pygame.Rect(self.rect.x + 30, y + 18, bar_width, 12)
            pygame.draw.rect(surface, config.COLOR_PANEL_ACCENT, bar_rect, border_radius=4)
            fill_rect = pygame.Rect(bar_rect.x, bar_rect.y, int(bar_rect.width * ratio), bar_rect.height)
            fill_color = config.COLOR_STATUS_POSITIVE if ratio >= 0.5 else config.COLOR_STATUS_NEGATIVE
            pygame.draw.rect(surface, fill_color, fill_rect, border_radius=4)
            text = self.small_font.render(f"{label} {value:.0f}", True, config.COLOR_TEXT_SECONDARY)
            surface.blit(text, (self.rect.x + 30, y))
            y += 36

    def _draw_satisfaction(self, surface: pygame.Surface) -> None:
        y = self.rect.y + 500
        header = self.font.render("Faction Satisfaction", True, config.COLOR_TEXT_PRIMARY)
        surface.blit(header, (self.rect.x + 30, y))
        y += 24
        bar_width = self.rect.width - 120
        entries = [
            ("Office Workers", self.game_state.satisfaction.civil_support),
            ("Agriculture Sector", self.game_state.satisfaction.agriculture_support),
            ("Students", self.game_state.satisfaction.education_support),
            ("Government", self.game_state.satisfaction.government_support),
        ]
        for label, value in entries:
            bar_rect = pygame.Rect(self.rect.x + 30, y + 14, bar_width, 10)
            pygame.draw.rect(surface, config.COLOR_PANEL_ACCENT, bar_rect, border_radius=4)
            fill_rect = pygame.Rect(bar_rect.x, bar_rect.y, int(bar_rect.width * value), bar_rect.height)
            pygame.draw.rect(surface, config.COLOR_STATUS_POSITIVE, fill_rect, border_radius=4)
            text = self.small_font.render(f"{label} {format_percentage(value)}", True, config.COLOR_TEXT_SECONDARY)
            surface.blit(text, (self.rect.x + 30, y))
            y += 24

    def _draw_calendar(self, surface: pygame.Surface) -> None:
        info = self.small_font.render(
            f"Year {self.game_state.current_year} Month {self.game_state.current_month} | {self.game_state.current_season}",
            True,
            config.COLOR_TEXT_SECONDARY,
        )
        surface.blit(info, (self.rect.x + 30, self.rect.y + 70))

    def _draw_events(self, surface: pygame.Surface, start_y: int) -> None:
        y = start_y
        header = self.font.render("Active Events", True, config.COLOR_TEXT_PRIMARY)
        surface.blit(header, (self.rect.x + 30, y))
        y += 30
        events = self.game_state.active_event_details
        if not events:
            text = self.small_font.render("No special events right now.", True, config.COLOR_TEXT_SECONDARY)
            surface.blit(text, (self.rect.x + 30, y))
            return
        for name, description in events:
            summary = self._truncate(description, 16)
            text = self.small_font.render(f"• {name}: {summary}", True, config.COLOR_TEXT_SECONDARY)
            surface.blit(text, (self.rect.x + 30, y))
            y += 24

    def _draw_spotlights(self, surface: pygame.Surface) -> int:
        y = self.rect.y + 620
        header = self.font.render("Island Pulse", True, config.COLOR_TEXT_PRIMARY)
        surface.blit(header, (self.rect.x + 30, y))
        y += 30
        entries = self.game_state.spotlights
        if not entries:
            text = self.small_font.render("No spotlight highlights yet.", True, config.COLOR_TEXT_SECONDARY)
            surface.blit(text, (self.rect.x + 30, y))
            return self.rect.y + 670

        for title, description in entries:
            title_text = self.small_font.render(f"• {title}", True, config.COLOR_TEXT_PRIMARY)
            surface.blit(title_text, (self.rect.x + 30, y))
            y += 20
            body_text = self.small_font.render(self._truncate(description, 24), True, config.COLOR_TEXT_SECONDARY)
            surface.blit(body_text, (self.rect.x + 46, y))
            y += 28

        return y + 10

    def _create_response_buttons(self) -> None:
        width = (self.rect.width - 90) // 2
        height = 32
        base_x = self.rect.x + 30
        base_y = self.rect.y + 400
        spacing_x = width + 30
        spacing_y = height + 14
        specs = [
            ("Boost Support", "campaign"),
            ("Summon Rain", "rain_ritual"),
            ("Fortify Grid", "reinforce_grid"),
            ("Renew Prayers", "renew_prayers"),
        ]
        buttons: list[Button] = []
        for index, (label, action_id) in enumerate(specs):
            row = index // 2
            col = index % 2
            rect = pygame.Rect(base_x + col * spacing_x, base_y + row * spacing_y, width, height)
            callback = lambda action=action_id: self.game_state.apply_response(action)
            buttons.append(Button(rect=rect, label=label, callback=callback))
        self.response_buttons = buttons

    @staticmethod
    def _truncate(text: str, limit: int) -> str:
        return text if len(text) <= limit else text[:limit] + "..."
