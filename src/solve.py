"""
Donat un puzzle, el resol.

Ús: python3 solve.py <puzzle.json>
"""

from graph import generar_graf, state_key, StateKey
from puzzle import Puzzle, State
from pathlib import Path
from logic import possible_moves, apply_move, is_goal

import sys
from typing import Optional

import graph_tool.all as gt  # type: ignore[import-untyped]

def solucio_puzzle(pz: Puzzle) -> None:
    """
    Donat un puzzle pz, genera un arxiu .sol.json, on resol el puzzle seguint el camí més ràpid possible.
    Aquesta funció fa servir l'algorisme BFS.
    """

    # s'importa el graf i els nodes destí del puzzle associat
    g, nodes_desti = generar_graf(pz)

    assert nodes_desti, "Aquest puzzle no té cap solució"

    # es troba el node origen, que correspon a l'estat inicial del taulell
    estat_inicial = state_key(pz, pz.start)
    node_inicial = gt.find_vertex(g, g.vp["state"], estat_inicial)

    # com que hi pot haver múltiples finals, busquem el camí més curt de tots
    distancia_minima = float('inf')
    millor_cami: Optional[tuple[list[gt.Vertex], list[gt.Edge]]] = None

    for desti in nodes_desti:
        # funció de graph-tool que fa un BFS
        llista_nodes, llista_arestes = gt.topology.shortest_path(g, node_inicial, desti)
        
        # es guarda el camí amb menys arestes, ja que és el que té menys moviments
        if len(llista_arestes) < distancia_minima:
            distancia_minima = len(llista_arestes)
            millor_cami = (llista_nodes, llista_arestes)

    # resultat
    llista_nodes_final, llista_arestes_final = millor_cami

    # HAY QUE ADAPTAR EL FORMATO PARA QUE SE PUEDA HACER SOL.JSON
    


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Ús: python3 {sys.argv[0]} <puzzle.json>")
        sys.exit(1)

    json_path = Path(sys.argv[1])
    pz = Puzzle.from_json(json_path.read_text())
    sol = solucio_puzzle(pz)

