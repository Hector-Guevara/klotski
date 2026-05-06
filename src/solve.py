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

    # mapa invers per recuperar la lletra de la direcció
    int_to_dir = {0: "N", 1: "E", 2: "S", 3: "W"}

    # com que hi pot haver múltiples finals, busquem el camí més curt de tots
    distancia_minima = float('inf')
    millor_cami: Optional[list[gt.Edge]] = None

    for desti in nodes_desti:
        # funció de graph-tool que fa un BFS
        llista_nodes, llista_arestes = gt.shortest_path(g, node_inicial, desti)
        
        # es guarda el camí amb menys arestes, ja que és el que té menys moviments
        if len(llista_arestes) < distancia_minima:
            distancia_minima = len(llista_arestes)
            millor_cami = llista_arestes

    # es construeix la llista en el format desitjat
    solucio_final = []
    for edge in millor_cami:
        m_data = g.ep["move"][edge] # es recupera el format [peça, dir, num_moviments]
        moviment = [int(m_data[0]), int_to_dir[m_data[1]], int(m_data[2])]
        solucio_final.append(moviment)

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
