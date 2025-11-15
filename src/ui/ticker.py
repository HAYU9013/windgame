"""即時新聞跑馬燈。"""
from __future__ import annotations

from typing import Iterable

import pygame

from .. import config


class NewsTicker:
    """將遊戲內訊息以跑馬燈方式顯示。"""

    def __init__(self, rect: pygame.Rect) -> None:
        self.rect = rect
        self.scroll_x = rect.width
        self.current_text = ""
        self.speed = 80  # 每秒像素
        self.text_width = rect.width
        self._last_snapshot: tuple[str, ...] = ()

    def update(self, dt: float, messages: Iterable[str]) -> None:
        snapshot = tuple(messages)
        if snapshot != self._last_snapshot:
            self._last_snapshot = snapshot
            base = "  |  ".join(snapshot) if snapshot else "暫無最新訊息"
            self.current_text = base
            self.scroll_x = self.rect.width
            self.text_width = max(self.rect.width, len(self.current_text) * 12)
        self.scroll_x -= self.speed * dt
        wrap_width = max(self.rect.width, self.text_width)
        if self.scroll_x < -wrap_width:
            self.scroll_x = self.rect.width

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, messages: Iterable[str]) -> None:
        if not self.current_text:
            snapshot = tuple(messages)
            self.current_text = "  |  ".join(snapshot) if snapshot else "暫無最新訊息"
        pygame.draw.rect(surface, config.COLOR_TICKER_BG, self.rect)
        text_surface = font.render(self.current_text, True, config.COLOR_TICKER_TEXT)
        surface.blit(text_surface, (self.scroll_x, self.rect.y + 20))
        self.text_width = text_surface.get_width()
