"""互動元件定義。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import pygame

from .. import config


@dataclass
class Button:
    rect: pygame.Rect
    label: str
    callback: Callable[[], None]
    active: bool = False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        color = config.COLOR_BUTTON_ACTIVE if self.active else config.COLOR_BUTTON_BG
        pygame.draw.rect(surface, color, self.rect, border_radius=6)
        text_surface = font.render(self.label, True, config.COLOR_TEXT_PRIMARY)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.callback()


@dataclass
class Slider:
    rect: pygame.Rect
    label: str
    value: float
    on_change: Callable[[float], None]
    dragging: bool = False
    suffix: Optional[str] = None

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, small_font: pygame.font.Font) -> None:
        pygame.draw.rect(surface, config.COLOR_SLIDER_TRACK, self.rect, border_radius=4)
        handle_x = int(self.rect.x + self.value * self.rect.width)
        handle_rect = pygame.Rect(handle_x - 8, self.rect.y - 4, 16, self.rect.height + 8)
        pygame.draw.rect(surface, config.COLOR_SLIDER_HANDLE, handle_rect, border_radius=6)

        label_surface = font.render(self.label, True, config.COLOR_TEXT_PRIMARY)
        surface.blit(label_surface, (self.rect.x, self.rect.y - 28))

        value_text = f"{self.value:.2f}" if not self.suffix else f"{self.value:.2f}{self.suffix}"
        value_surface = small_font.render(value_text, True, config.COLOR_TEXT_SECONDARY)
        surface.blit(value_surface, (self.rect.right - value_surface.get_width(), self.rect.y - 24))

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.dragging = True
                self._update_value(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging:
                self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._update_value(event.pos[0])

    def _update_value(self, mouse_x: int) -> None:
        ratio = (mouse_x - self.rect.x) / self.rect.width
        new_value = max(0.0, min(1.0, ratio))
        if abs(new_value - self.value) > 0.001:
            self.value = new_value
            self.on_change(self.value)
