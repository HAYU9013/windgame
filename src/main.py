"""pygame 進入點。"""
from __future__ import annotations

import sys
from pathlib import Path

import pygame

from . import config
from .data_loader import DataRepository
from .game_state import GameState
from .ui.components import Button
from .ui.map_view import MapView
from .ui.panel import ControlPanel
from .ui.ticker import NewsTicker


def _load_font(size: int) -> pygame.font.Font:
    font_path = config.FONT_PATH
    if font_path:
        try:
            return pygame.font.Font(str(font_path), size)
        except (FileNotFoundError, OSError):
            pass
    return pygame.font.Font(None, size)


def load_fonts() -> tuple[pygame.font.Font, pygame.font.Font, pygame.font.Font]:
    title_font = _load_font(config.TITLE_FONT_SIZE)
    text_font = _load_font(config.TEXT_FONT_SIZE)
    small_font = _load_font(config.SMALL_FONT_SIZE)
    return title_font, text_font, small_font


def create_time_buttons(game_state: GameState, font: pygame.font.Font) -> list[Button]:
    base_x = config.PANEL_AREA[0] + 40
    base_y = config.SCREEN_HEIGHT - 140
    width = 100
    spacing = 120

    def make_callback(scale: int):
        return lambda: game_state.change_time_scale(scale)

    buttons = [
        Button(pygame.Rect(base_x + idx * spacing, base_y, width, 40), label, make_callback(scale))
        for idx, (label, scale) in enumerate([("暫停", 0), ("正常", 1), ("快轉", 2)])
    ]
    for button in buttons:
        button.draw_font = font  # type: ignore[attr-defined]
    return buttons


def update_button_state(buttons: list[Button], game_state: GameState) -> None:
    mapping = {"暫停": 0, "正常": 1, "快轉": 2}
    for button in buttons:
        button.active = mapping.get(button.label, -1) == game_state.time_scale


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    pygame.display.set_caption("風巡者：天氣之神")
    clock = pygame.time.Clock()

    repository = DataRepository(Path(__file__).resolve().parent.parent)
    game_state = GameState(repository)

    title_font, text_font, small_font = load_fonts()
    map_view = MapView(pygame.Rect(*config.MAP_AREA))
    control_panel = ControlPanel(pygame.Rect(*config.PANEL_AREA), game_state, text_font, small_font)
    ticker = NewsTicker(pygame.Rect(*config.TICKER_AREA))
    time_buttons = create_time_buttons(game_state, text_font)

    running = True
    while running:
        dt = clock.tick(config.FPS) / 1000
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            control_panel.handle_event(event)
            for button in time_buttons:
                button.handle_event(event)

        simulation_speed = {0: 0.0, 1: 1.0, 2: 3.0}[game_state.time_scale]
        game_state.step_simulation(dt * simulation_speed * 6)  # 將秒數轉換為小時進程

        ticker.update(dt, game_state.news)
        update_button_state(time_buttons, game_state)

        screen.fill(config.COLOR_BACKGROUND)
        map_view.draw(screen, repository.regions, repository.reservoirs, small_font)
        control_panel.draw(screen)

        for button in time_buttons:
            button.draw(screen, text_font)

        ticker.draw(screen, text_font, game_state.news)
        pygame.display.flip()

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
