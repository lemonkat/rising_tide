from __future__ import annotations

import random
import time
import traceback
import typing
import contextlib

import numpy as np

import util

RNG = np.random.default_rng()

class PrintRedirectorStream:
    """
    a system to redirect bot print statements to the log file
    """

    def __init__(self, plr_name: str, log_fn: typing.Callable[..., None]):
        self.plr_name = plr_name
        self.log_fn = log_fn
        self.has_written = False

    def write(self, val: str) -> None:
        if not self.has_written:
            self.log_fn(f"{self.plr_name} has printed: ")
            self.has_written = True
        self.log_fn(val)

class Board:
    """
    Class representing the game board
    """
    def __init__(
        self,
        bots: list[util.Bot],
        log_path: typing.Optional[str] = "log.txt",
    ) -> None:
        self.bots = bots
        self.round_num = 0
        self.terrain = np.copy(util.START_TERRAIN)
        self.scores = [-1] * 4

        if log_path:
            self.log_file = open(log_path, "w")
        else:
            self.log_file = None

        self.logged_round = False

        self.log("[GAME START]", f"BOTS: {', '.join(bot.name for bot in bots)}")

    @property
    def alive(self) -> list[bool]:
        return [self.terrain[i, j] != -1 for i, j in util.CITIES]
    
    @property
    def running(self) -> bool:
        return sum(self.alive) > 1 and self.round_num * util.SINK_RATE < 8

    def log(self, *data: object) -> None:
        """
        write things to the log file, 
        add the round number if this is the first log message this round
        """
        if self.log_file is None:
            return
        if not self.logged_round:
            self.logged_round = True
            print(f"[R{self.round_num}]", file=self.log_file)
        
        print(*data, sep="\n", file=self.log_file, flush=True)
    
    def get_move(self, bot_idx: int) -> tuple[tuple[int, int], tuple[int, int]] | None:
        """
        return a valid move from a bot
        if bot returns invalid move or throws error, log it
        """
        bot = self.bots[bot_idx]
        terrain = util.copy_grid(np.rot90(self.terrain, bot_idx))
        try:
            t0 = time.time()
            with contextlib.redirect_stdout(PrintRedirectorStream(bot.name, self.log)):
                move_raw = bot.func(terrain, self.round_num)
            t1 = time.time()
            
            if t1 - t0 > 0.1:
                self.log(
                    f"{bot.name} is taking too long.",
                    "Your bot will forfeit its turn. ",
                    f"time: {(t1 - t0) * 1000} ms",
                    f"move: {move_raw}",
                )
                return None
            
        except Exception:
            self.log(
                f"{bot.name} has thrown an error. ",
                "Your bot will forfeit its turn. ",
                traceback.format_exc(),
            )
            return None

        try:
            if move_raw is None:
                return None
                
            (i0, j0), (i1, j1) = move_raw
            if not all(isinstance(num, int) for num in [i0, i1, j0, j1]):
                raise TypeError(f"Wrong type for move: {move_raw}")
            
            src, dst = (i0, j0), (i1, j1)
            
            if not util.is_legal(terrain, src, dst):
                self.log(
                    f"{bot.name} has made an illegal move. ",
                    f"move: {move_raw}",
                )
                return None

        except (TypeError, ValueError, IndexError, AttributeError):
            self.log(
                f"{bot.name} has made a non-parseable move. ",
                f"move: {move_raw}",
                traceback.format_exc(),
            )
            return None

        return util.rotate_move(4 - bot_idx, (src, dst))


    def step(self) -> None:
        """
        run a single round of the game
        """
        self.logged_round = False

        moves = [self.get_move(i) for i in range(4) if self.alive[i]]

        random.shuffle(moves)
        for move in moves:
            if move is None:
                continue
            src, dst = move
            if util.is_legal(self.terrain, src, dst):
                self.terrain[src] -= 1
                self.terrain[dst] += 1

        self.terrain[...] = util.flood(self.terrain, self.round_num)

        for i in range(4):
            if self.scores[i] == -1 and self.terrain[util.CITIES[i]] == -1:
                self.log(f"{self.bots[i].name} ELIMINATED")
                self.scores[i] = self.round_num

        self.round_num += 1

        if not self.running:
            self.end_game()

    def end_game(self) -> None:
        """
        finalize scores and log the end of the game
        """
        self.scores = [800 if score == -1 else score for score in self.scores]

        self.log(
            "[GAME OVER]", 
            "SCORES: ",
            *[f"{self.bots[i].name}: {self.scores[i]}" for i in range(4)],
        )