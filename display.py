import time
import textwrap
import typing

import numpy as np

import display_grid as dg

import util
import board

# 11 colors + sunk
COLORS = np.array(
    [
        [0xff, 0x00, 0x00],
        [0xff, 0x5f, 0x00],
        [0xff, 0x87, 0x00],
        [0xff, 0xaf, 0x00],
        [0xff, 0xd7, 0x00],
        [0xff, 0xff, 0x00],
        [0xd7, 0xff, 0x00],
        [0xaf, 0xff, 0x00],
        [0x00, 0xff, 0x00],
        [0x00, 0x00, 0xff],
    ],
    dtype=np.uint8,
)

class RTDisplayMap(dg.Module):
    """
    dg.Module showing a map of the island
    """
    def __init__(
        self, 
        parent: dg.Module, 
        board: board.Board,
    ) -> None:
        super().__init__(parent, (1, 2, 23, 46))
        self.board = board

    def _draw(self) -> None:
        self.grid.fill(char=" ", bg=COLORS[-1])

        map_colors = COLORS[np.minimum(self.board.terrain, 8)]
        self.grid.bg[2:-2, 4:-4:2] = map_colors
        self.grid.bg[2:-2, 5:-4:2] = map_colors

        self.grid.print("RISING TIDE", pos=(0, 2), attrs=dg.TA_BOLD | dg.TA_ITALIC)

        self.grid.print("N", pos=(19, 2))
        self.grid.print("W+E", pos=(20, 1))
        self.grid.print("S", pos=(21, 2))

        for idx, (i, j) in enumerate(util.CITIES):
            if self.board.alive[idx]:
                self.grid.print(
                    self.board.bots[idx].code, 
                    pos=(2 + i, 4 + 2 * j), 
                    fg=[255, 255, 255], 
                    bg=[0, 0, 0],
                )
        

class RTDisplayStats(dg.Module):
    """
    dg.Module showing game stats and water level
    """
    def __init__(
        self, 
        parent: dg.Module, 
        board: board.Board,
    ) -> None:
        super().__init__(parent, (1, 48, 23, 78))
        self.board = board
        self.bar = RTDisplayBar(self, board)
    
    def _draw(self) -> None:
        self.grid.clear()
        self.grid.print(f"ROUND {self.board.round_num:4d}", pos=(1, 15))

        for i, bot in enumerate(self.board.bots):
            
            status = "  ALIVE" if self.board.scores[i] in [-1, 800] else f"  SUNK R{self.board.scores[i]}"
            lines = textwrap.wrap(bot.code + " | " + bot.name, 14) + [status]
            for j, line in enumerate(lines):
                self.grid.print(line, pos=(3 + 4 * i + j, 15))

class RTDisplayBar(dg.Module):
    """
    dg.Module that draws the water level itself
    """
    def __init__(
        self, 
        parent: dg.Module, 
        board: board.Board,
    ) -> None:
        super().__init__(parent, (1, 2, 21, 14))
        self.board = board

    def _draw(self) -> None:
        self.grid.print("WATER LEVEL", pos=(0, 0))

        self.grid.fg[2:, 3:11] = COLORS[-1]
        self.grid.bg[2:, 5:9] = np.repeat(COLORS[-2::-1], 2, axis=0)[:, None]
        self.grid.fg[2:, 5:9] = 0.5 * self.grid.bg[2:, 5:9] + [0, 0, 120]

        water_level = 2 * self.board.round_num * util.SINK_RATE
        self.grid.chars[19 - int(water_level):, 3:11] = ord("█")
        self.grid.chars[19 - int(water_level), 3:11] = ord(dg.util.BLOCKS[int((water_level - int(water_level)) * 8) % 8])
        
        for i in range(9):
            self.grid.print(8 - i, pos=(2 * i + 2, 0))

class RTDisplayMain(dg.Module):
    """
    main dg.Module for showing a game of Rising Tide
    """
    def __init__(
        self, 
        parent: dg.Module, 
        board: board.Board,
    ) -> None:
        super().__init__(parent, (0, 0, 24, 80))
        self.board = board
        self.map = RTDisplayMap(self, board)
        self.stats = RTDisplayStats(self, board)

    def _tick(self) -> None:
        if self.board.running:
            self.board.step()

    def _draw(self) -> None:
        self.grid.clear()
        self.grid.fill("#")

def run_game(
    bots: tuple[util.Bot, util.Bot, util.Bot, util.Bot], 
    mode: str = "terminal",
    pause_on_end: bool = True,
    log_path: typing.Optional[str] = "log.txt",
) -> tuple[int, int, int, int]:
    """
    run a game with the following bots, display mode, and log file, returning scores
    """
    game_board = board.Board(bots, log_path)
    if mode == "none":
        while game_board.running:
            game_board.step()
    else:
        with dg.MainModule((24, 80), enforce_shape=False, mode=mode) as main_module:
            rt_display = RTDisplayMain(
                main_module,
                board.Board(bots)
            )
            dg.modules.KeyTrigger(main_module, fn=lambda: rt_display.start() if rt_display.paused else rt_display.stop())
            try:
                while pause_on_end or game_board.running:
                    t0 = time.time()
                    main_module.tick()
                    main_module.draw()
                    time.sleep(max(0, 1 / 60 + t0 - time.time()))
            except KeyboardInterrupt:
                pass
    return game_board.scores