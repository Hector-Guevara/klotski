"""
Donat un puzzle, el resol.

Ús: python3 solve.py <puzzle.json>
"""

from graph import generar_graf, state_key
from puzzle import Puzzle, State
from pathlib import Path
from logic import possible_moves, apply_move

import sys

import graph_tool.all as gt  # type: ignore[import-untyped]

def solucio_puzzle(pz: Puzzle) -> None:
    """
    Donat un puzzle pz, genera un arxiu .sol.json, on resol el puzzle seguint el camí més ràpid possible.
    Aquesta funció fa servir l'algorisme A* (o BFS, pendiente de revisión).
    """

    g = generar_graf(pz)

    # es troba el node origen

    # Obtienes la huella dactilar del estado inicial
    start_key = state_key(pz, pz.start) 

    # Buscas el nodo que tiene esa huella en la propiedad "state"
    nodos_encontrados = gt.find_vertex(g, g.vp["state"], start_key)

    # Como sabes que solo hay uno, te quedas con el primero de la lista
    v_origen = nodos_encontrados[0]

    # s'identifiquen els nodes destí

    # es troba el camí més curt, fent servir les funcions de graph-tool 

    camins = gt.topology.shortest_path(g, node_origen, node_desti)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Ús: python3 {sys.argv[0]} <puzzle.json>")
        sys.exit(1)

    json_path = Path(sys.argv[1])
    pz = Puzzle.from_json(json_path.read_text())
    sol = solucio_puzzle(pz)

