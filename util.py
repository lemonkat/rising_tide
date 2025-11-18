import typing

import numpy as np

BOARD_SIZE = 18

CITIES = [
    (5, 5),
    (5, 12),
    (12, 12),
    (12, 5),
]

SINK_RATE = 1 / 100

START_TERRAIN = np.full((BOARD_SIZE, BOARD_SIZE), 1, dtype=np.int32)

for i in range(BOARD_SIZE // 2):
    START_TERRAIN[i:-i, i:-i] = min(i, 5) + 1

for city in CITIES:
    START_TERRAIN[city] = 0

def copy_grid(grid: list[list[int]]) -> list[list[int]]:
    """
    given a list of lists, deep-copy the thing into another list of lists
    """
    return [[int(num) for num in row] for row in grid]

def dist(a: tuple[int], b: tuple[int]) -> int:
    """
    returns the taxicab distance between 2 points
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

NEARBY_TABLE = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=object)
for i, j in np.ndindex((BOARD_SIZE, BOARD_SIZE)):
    result = np.clip(np.mgrid[-1:2, -1:2].T.reshape(-1, 2) + (i, j), 0, BOARD_SIZE - 1)
    NEARBY_TABLE[i, j] = {(int(i1), int(j1)) for (i1, j1) in map(tuple, result) if (i1, j1) != (i, j)}

def nearby(pos: tuple[int, int]) -> set[tuple[int, int]]:
    """
    returns the set of points neighboring pos
    """
    return NEARBY_TABLE[pos]
    
def in_bounds(pos: tuple[int, int]) -> bool:
    """
    returns if pos is in bounds
    """
    return 0 <= pos[0] < BOARD_SIZE and 0 <= pos[1] < BOARD_SIZE

def is_legal(
    terrain: list[list[int]], src: tuple[int, int], dst: tuple[int, int]
) -> bool:
    """
    return whether or not a move is legal
    """
    if not in_bounds(src) or not in_bounds(dst):
        return False
    if terrain[src[0]][src[1]] <= 0:
        return False
    if terrain[dst[0]][dst[1]] == -1 or terrain[dst[0]][dst[1]] == 8:
        return False
    return src not in CITIES and dst not in CITIES

def allowed_moves(terrain: list[list[int]]) -> set[tuple[tuple[int, int], tuple[int, int]]]:
    """
    returns the set of all legal moves for the given terrain.
    """
    allowed = set()
    for i in range(BOARD_SIZE):
        for j in range(BOARD_SIZE):
            for dst in nearby((i, j)):
                if is_legal(terrain, (i, j), dst):
                    allowed.add(((i, j), dst))
    return allowed

def is_near_water(terrain: list[list[int]], pos: tuple[int, int]) -> bool:
    """
    returns whether or not a position is next to a flooded tile
    """
    for pos2 in nearby(pos):
        if terrain[pos2[0]][pos2[1]] == -1:
            return True
    return 0 in pos or BOARD_SIZE - 1 in pos    

def rotate_move(
    plr: int, move: tuple[tuple[int, int], tuple[int, int]] | None
) -> tuple[tuple[int, int], tuple[int, int]] | None:
    """
    rotates a move from bot's POV to main POV
    """
    if move is None:
        return None
    (i1, j1), (i2, j2) = move
    for _ in range(plr):
        i1, j1 = BOARD_SIZE - 1 - j1, i1
        i2, j2 = BOARD_SIZE - 1 - j2, i2
    return (i1, j1), (i2, j2)

# arrays to hold stuff in and save a little time
_FLOOD_TEMP_A = np.ones((BOARD_SIZE, BOARD_SIZE), dtype=bool)
_FLOOD_TEMP_B = np.lib.stride_tricks.sliding_window_view(
    np.ones((BOARD_SIZE + 2, BOARD_SIZE + 2), dtype=bool), 
    (BOARD_SIZE, BOARD_SIZE), 
    writeable=True,
)
_FLOOD_TEMP_BX = _FLOOD_TEMP_B[1, 1]
def flood(terrain: list[list[int]], round_num: int) -> list[list[int]]:
    """
    run the flooding step
    this function is real advanced here just trust me it works
    """
    terrain = np.array(terrain, dtype=np.int32)
    np.less(terrain, round_num * SINK_RATE, out=_FLOOD_TEMP_A)
    np.signbit(terrain, out=_FLOOD_TEMP_BX)
    np.any(_FLOOD_TEMP_B, axis=(0, 1), out=_FLOOD_TEMP_BX)
    np.logical_and(_FLOOD_TEMP_A, _FLOOD_TEMP_BX, out=_FLOOD_TEMP_A)
    terrain[_FLOOD_TEMP_A] = -1
    return copy_grid(terrain)

class Bot(typing.NamedTuple):
    name: str
    code: str
    func: typing.Callable[
        [list[list[int]], int], tuple[tuple[int, int], tuple[int, int]] | None
    ]

def make_bot(
    name: str,
    code: str,
    func: typing.Callable[
        [list[list[int]], int], tuple[tuple[int, int], tuple[int, int]] | None
    ],
) -> Bot:
    """
    construct a bot
    """
    return Bot(name, code, func)