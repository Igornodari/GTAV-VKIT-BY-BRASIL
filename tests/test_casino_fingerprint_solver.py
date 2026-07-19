from solvers.casinofingerprint import find_shortest_solution

ROWS, COLS = 4, 2
STEP = {"s": (0, 1), "d": (1, 0), "w": (0, -1), "a": (-1, 0)}


def _apply_move(pos, key):
    """Mirror the exact wrap logic used by find_shortest_solution's BFS."""
    x, y = pos
    dx, dy = STEP[key]
    x, y = x + dx, y + dy
    if x == -1:
        x, y = COLS - 1, y - 1
    elif x == COLS:
        x, y = 0, y + 1
    y %= ROWS
    return (x, y)


def _simulate(moves):
    """Replay a move sequence, returning the cells flagged by 'return'."""
    pos = (0, 0)
    reached = set()
    for move in moves:
        if move == "tab":
            continue
        if move == "return":
            reached.add(pos)
            continue
        pos = _apply_move(pos, move)
    return reached


def test_ends_with_tab():
    moves = find_shortest_solution([(0, 0)])
    assert moves[-1] == "tab"


def test_visits_target_at_origin_with_no_movement():
    moves = find_shortest_solution([(0, 0)])
    assert _simulate(moves) == {(0, 0)}
    assert moves == ["return", "tab"]


def test_visits_adjacent_target_in_one_step():
    moves = find_shortest_solution([(1, 0)])
    assert _simulate(moves) == {(1, 0)}
    # shortest path to an orthogonal neighbour is a single move + return + tab
    assert len(moves) == 3


def test_visits_all_of_multiple_targets():
    targets = [(1, 0), (0, 2)]
    moves = find_shortest_solution(targets)
    assert _simulate(moves) == set(targets)


def test_wraps_around_grid_edges():
    # column wraps from x=-1 back to the last column, one row up
    targets = [(1, 3)]
    moves = find_shortest_solution(targets)
    assert _simulate(moves) == {(1, 3)}
