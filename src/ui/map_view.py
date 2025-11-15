"""地圖呈現。"""
from __future__ import annotations

from typing import Iterable, Optional

import pygame

from .. import config
from ..data_loader import Region, Reservoir


class MapView:
    def __init__(self, rect: pygame.Rect) -> None:
        self.rect = rect
        self._map_surface = self._load_surface(config.MAP_BASE_IMAGE)
        self._relief_surface = self._load_surface(config.MAP_RELIEF_IMAGE)
        self._map_polygon = self._build_placeholder_polygon(rect)

    def draw(
        self,
        surface: pygame.Surface,
        regions: Iterable[Region],
        reservoirs: Iterable[Reservoir],
        font: pygame.font.Font,
    ) -> None:
        pygame.draw.rect(surface, config.COLOR_MAP, self.rect, border_radius=10)

        if self._map_surface:
            surface.blit(self._map_surface, self.rect)
            if self._relief_surface:
                surface.blit(self._relief_surface, self.rect)
        else:
            self._draw_placeholder(surface)

        for region in regions:
            x, y = region.coordinates
            pygame.draw.circle(surface, (90, 140, 180), (x, y), 10)
            label = font.render(region.name, True, config.COLOR_TEXT_PRIMARY)
            surface.blit(label, (x + 12, y - 10))

        for reservoir in reservoirs:
            x, y = reservoir.coordinates
            pygame.draw.circle(surface, (120, 200, 255), (x, y), 8)
            ratio = reservoir.storage / reservoir.capacity if reservoir.capacity else 0
            label = font.render(f"{reservoir.name} {int(ratio * 100)}%", True, config.COLOR_TEXT_SECONDARY)
            surface.blit(label, (x + 10, y + 6))

    def _load_surface(self, path: Optional[object]) -> Optional[pygame.Surface]:
        if not path:
            return None
        try:
            image = pygame.image.load(str(path)).convert_alpha()
        except (pygame.error, FileNotFoundError):
            return None
        return pygame.transform.smoothscale(image, self.rect.size)

    def _draw_placeholder(self, surface: pygame.Surface) -> None:
        placeholder_rect = self.rect.inflate(-16, -16)
        pygame.draw.rect(surface, (42, 74, 102), placeholder_rect, border_radius=12)
        pygame.draw.rect(surface, (68, 109, 143), placeholder_rect, width=3, border_radius=12)
        pygame.draw.polygon(surface, (24, 90, 128), self._map_polygon)
        pygame.draw.polygon(surface, (41, 118, 160), self._map_polygon, width=3)

    @staticmethod
    def _build_placeholder_polygon(rect: pygame.Rect) -> list[tuple[int, int]]:
        return [
            (rect.x + 260, rect.y + 40),
            (rect.x + 340, rect.y + 60),
            (rect.x + 420, rect.y + 120),
            (rect.x + 450, rect.y + 220),
            (rect.x + 420, rect.y + 330),
            (rect.x + 360, rect.y + 420),
            (rect.x + 320, rect.y + 520),
            (rect.x + 260, rect.y + 600),
            (rect.x + 200, rect.y + 520),
            (rect.x + 160, rect.y + 420),
            (rect.x + 170, rect.y + 320),
            (rect.x + 190, rect.y + 220),
            (rect.x + 220, rect.y + 130),
        ]

