"""
Donat un puzzle, el resol.

Ús: python3 solve.py <puzzle.json>
"""

from graph import generar_graf, state_key, StateKey
from puzzle import Puzzle, State
from pathlib import Path
from logic import possible_moves, apply_move, is_goal

import sys
import json
from typing import Optional
from collections import deque

import graph_tool.all as gt  # type: ignore[import-untyped]

def solucio_puzzle(pz: Puzzle, output_path: Path) -> None:
    """
    Donat un puzzle pz, genera un arxiu .sol.json, on resol el puzzle seguint el camí més ràpid possible.
    Aquesta funció fa servir l'algorisme BFS.
    """

    # s'importa el graf i els nodes destí del puzzle associat
    g, nodes_desti = generar_graf(pz)

    assert nodes_desti, "Aquest puzzle no té cap solució"

    # es troba el node origen, que correspon a l'estat inicial del taulell
    estat_inicial = state_key(pz, pz.start)
    node_inicial = gt.find_vertex(g, g.vp["state"], estat_inicial)[0]
    millor_nodes = None

    # mapa invers per recuperar la lletra de la direcció
    int_to_dir = {0: "N", 1: "E", 2: "S", 3: "W"}

    # com que hi pot haver múltiples finals, busquem el camí més curt de tots
    distancia_minima = float('inf')
    millor_cami: Optional[list[gt.Edge]] = None

    for desti in nodes_desti:

        llista_nodes, llista_arestes = gt.shortest_path(g, node_inicial, desti)

        if len(llista_arestes) < distancia_minima:
            distancia_minima = len(llista_arestes)
            millor_cami = llista_arestes
            millor_nodes = llista_nodes


    solucio_final = []

    # estado real inicial
    estat_actual = pz.start

    for i in range(len(millor_nodes) - 1):

        key_actual = g.vp["state"][millor_nodes[i]]
        key_seguent = g.vp["state"][millor_nodes[i + 1]]

        # BFS local entre representatives reals
        cua = deque()
        cua.append((estat_actual, []))

        visitats = set()
        visitats.add(tuple(tuple(p) for p in estat_actual.positions))

        trobat = False

        while cua and not trobat:

            estat, cami = cua.popleft()

            # si arribem al següent estat canònic
            if state_key(pz, estat) == key_seguent and cami:

                # afegim els moviments trobats
                for mov in cami:
                    p_idx, direction, dist = mov
                    solucio_final.append([p_idx, direction, dist])

                estat_actual = estat
                trobat = True
                break

            # expandim moviments reals
            for move in possible_moves(pz, estat):

                nou_estat = apply_move(pz, estat, move)

                real_key = tuple(tuple(p) for p in nou_estat.positions)

                if real_key in visitats:
                    continue

                # IMPORTANT:
                # només explorem estats que:
                #   - segueixen al node actual
                #   - o arriben al següent
                canonical = state_key(pz, nou_estat)

                if canonical not in (key_actual, key_seguent):
                    continue

                visitats.add(real_key)

                cua.append((nou_estat, cami + [move]))

    assert trobat

    # es guarda el fitxer json
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
