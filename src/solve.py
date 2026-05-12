"""
Donat un puzzle, el resol.

Ús: python3 solve2.py <puzzle.json>
"""

from graph import generar_graf, state_key
from puzzle import Puzzle
from logic import possible_moves, apply_move, is_goal
from pathlib import Path

import sys
import json
from collections import deque

import graph_tool.all as gt  # type: ignore[import-untyped]


def solucio_puzzle(pz: Puzzle, output_path: Path) -> None:
    """
    Donat un puzzle pz, genera un arxiu .sol.json amb la seqüència de moviments
    mínima per resoldre'l.

    Fa servir el graf per obtenir les claus canòniques dels nodes destí,
    però resol el puzzle amb un BFS directe sobre estats reals, garantint
    que els índexos de les peces sempre són correctes.
    """

    g, nodes_desti = generar_graf(pz)
    assert nodes_desti, "Aquest puzzle no té cap solució"

    # claus canòniques dels estats finals
    claus_desti = {g.vp["state"][v] for v in nodes_desti}

    # BFS sobre estats reals (amb índexos de peça fixos)
    cua: deque[tuple] = deque([(pz.start, [])])
    visitats: set = {tuple(pz.start.positions)}

    solucio_final = None

    while cua:
        estat, cami = cua.popleft()

        if state_key(pz, estat) in claus_desti:
            solucio_final = cami
            break

        for move in possible_moves(pz, estat):
            nou_estat = apply_move(pz, estat, move)
            real_key = tuple(nou_estat.positions)
            if real_key not in visitats:
                visitats.add(real_key)
                cua.append((nou_estat, cami + [move]))

    assert solucio_final is not None, "Aquest puzzle no té cap solució"

    with open(output_path, 'w') as f:
        json.dump(solucio_final, f)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Ús: python3 {sys.argv[0]} <puzzle.json>")
        sys.exit(1)

    puzzle_path = Path(sys.argv[1])
    puzzle = Puzzle.from_json(puzzle_path.read_text())

    sol_path = puzzle_path.with_suffix(".sol.json")
    solucio_puzzle(puzzle, sol_path)
