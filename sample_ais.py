import random

import util

def pass_bot_fn(terrain, round_num):
    return None

pass_perth = util.make_bot("Pass Perth", "PR", pass_bot_fn)

def random_bot_fn(terrain, round_num):
    moves = util.allowed_moves(terrain)
    return random.choice(list(moves))

random_rizhao = util.make_bot("Random Rizhao", "RZ", random_bot_fn)

def nearby_bot_fn(terrain, round_num):
    moves = list(util.allowed_moves(terrain))
    scores = [util.dist((5, 5), dst) for src, dst in moves]
    best_score = min(scores)
    return random.choice([move for move, score in zip(moves, scores) if score == best_score])

nearby_new_orleans = util.make_bot("Nearby New Orleans", "NO", nearby_bot_fn)

def trench_bot_fn(terrain: list[list[int]], round_num: int) -> tuple[tuple[int, int], tuple[int, int]]:
    moves = util.allowed_moves(terrain)
    scores = []
    for src, dst in moves:
        score = float("inf")
        if util.is_near_water(terrain, src):
            for city in util.CITIES[1:]:
                score = min(score, util.dist(src, city))
        scores.append(score)
    min_score = min(scores)
    return random.choice([move for move, score in zip(moves, scores) if score == min_score])

trench_tunis = util.make_bot("Trench Tunis", "TN", trench_bot_fn)

def border_bot_fn(terrain, round_num):
    moves = list(util.allowed_moves(terrain))
    random.shuffle(moves)
    for src, dst in moves:
        if util.is_near_water(terrain, dst) and not util.is_near_water(terrain, src):
            return src, dst
    return moves[0]

border_barcelona = util.make_bot("Border Barcelona", "BC", border_bot_fn)

def level_bot_fn(terrain, round_num):
    moves = list(util.allowed_moves(terrain))
    random.shuffle(moves)
    for src, dst in moves:
        if max(*src, *dst) < 10 and terrain[src[0]][src[1]] > terrain[dst[0]][dst[1]]:
            return src, dst
    return moves[0]

level_los_angeles = util.make_bot("Level Los Angeles", "LA", level_bot_fn)

if __name__ == "__main__":
    from display import run_game
    run_game(
        [
            random_rizhao,
            nearby_new_orleans,
            border_barcelona,
            trench_tunis,
        ],
        mode="terminal",
    )