"""
Donat un puzzle, el resol.
 
Ús: python3 solve.py <puzzle.json>
"""
 
#from graph import generar_graf, state_key-----------Con las nuevas implementaciones no usamos estas funciones
from puzzle import Puzzle, State
from pathlib import Path
from logic import possible_moves, apply_move, is_goal
 
import sys
import json
from collections import deque
from typing import Optional
 
#import graph_tool.all as gt  # type: ignore[import-untyped]-----------Con las nuevas implementaciones no es necesario importar la libreria, no la usamos
 
 
def _bfs_real(pz: Puzzle) -> Optional[list]:
    """
    BFS directe sobre estats reals del puzzle.
    Retorna la llista de moviments [peça, direcció, dist] òptima,
    o None si el puzzle no té solució.
 
    Aquest enfocament evita el problema de la versió anterior, on
    la reconstrucció del camí a partir del graf canònic podia introduir
    moviments innecessaris: una aresta del graf canònic pot correspondre
    a múltiples moviments reals, i llegir g.ep["move"] directament
    només en recuperava un, que no necessàriament era el més curt.
    """
    estat_inicial = pz.start
 
    # cua de BFS: cada element és (estat_actual, camí_de_moviments_fins_aquí)
    cua: deque[tuple[State, list]] = deque()
    cua.append((estat_inicial, []))
 
    # conjunt de posicions visitades per evitar cicles
    visitats: set[tuple] = set()
    visitats.add(tuple(tuple(p) for p in estat_inicial.positions))
 
    while cua:
        estat, cami = cua.popleft()
 
        # si hem arribat a un estat final, retornem el camí
        if is_goal(pz, estat):
            return cami
 
        # expandim tots els moviments possibles d'un sol pas
        for move in possible_moves(pz, estat):
            nou_estat = apply_move(pz, estat, move)
            clau = tuple(tuple(p) for p in nou_estat.positions)
 
            if clau in visitats:
                continue
 
            visitats.add(clau)
            p_idx, direction, dist = move
            cua.append((nou_estat, cami + [[p_idx, direction, dist]]))
 
    # si la cua s'esgota sense trobar solució
    return None
 
 
def solucio_puzzle(pz: Puzzle, output_path: Path) -> None:
    """
    Donat un puzzle pz, genera un arxiu .sol.json amb la seqüència òptima
    de moviments per resoldre'l.
 
    Fa servir el graf per verificar que el puzzle és resoluble i obtenir
    la distància mínima esperada, però la reconstrucció del camí es fa
    amb un BFS directe sobre estats reals per garantir l'optimalitat.
    """
 
    # BFS directe sobre estats reals: garanteix el camí òptim sense artefactes
    # del graf canònic (on una aresta pot amagar múltiples moviments reals)
    solucio_final = _bfs_real(pz)
 
    assert solucio_final is not None, "El puzzle és resoluble però el BFS no ha trobat solució"
 
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