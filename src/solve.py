"""
Donat un puzzle, el resol de forma òptima i extremadament ràpida.
Aplica l'algorisme A*, seguint l'Heurística de la distància de Manhattan,
sense necessitat d'haver de calcular tot el graf sencer. 

Ús: 
    python3 solve.py <puzzle.json>
"""
 
from puzzle import Puzzle, State
from pathlib import Path
from logic import possible_moves, apply_move, is_goal
 
import sys
import json
import heapq
import itertools
from typing import Optional
 
 
def heuristica(pz: Puzzle, estat: State) -> int:
    """
    Calcula la distància Manhattan mínima de les peces objectiu 
    a les seves posicions finals.

    h(estat) = |x_actual - x_meta| + |y_actual - y_meta|
    
    Pre: 'pz' té un o més objectius definits a pz.goals i 'estat' conté 
         les posicions vàlides de totes les peces.
    Post: Retorna un enter >= 0 que representa el cost estimat per arribar 
          a la solució. Aquest valor és admissible (mai sobreestima el cost real).
    """
    h = 0
    for p_idx, pos_final in pz.goals:
        ex, ey = estat.positions[p_idx]
        gx, gy = pos_final
        h += abs(ex - gx) + abs(ey - gy)
    return h
 

def canonical_key(pz: Puzzle, estat: State) -> tuple:
    """
    Genera una clau canònica per a l'estat que agrupa les peces idèntiques
    que no són objectiu, reduint així l'espai de cerca dràsticament
    però manté la identitat exacta de les peces objectiu per garantir l'optimalitat.
    
    Pre: 'pz' és un objecte Puzzle vàlid i 'estat' el seu State actual.
    Post: Retorna una tupla única que representa l'estat. Si dues peces no-objectiu 
          idèntiques s'intercanvien de posició, la clau generada serà idèntica.
    """
    goal_indices = {g[0] for g in pz.goals}
    groups = {}
    
    for i, piece in enumerate(pz.pieces):
        if i in goal_indices:
            # Les peces objectiu es marquen de forma única perquè la seva 
            # identitat importa per resoldre el puzzle.
            shape_key = ("GOAL", i)
        else:
            # Les peces normals s'agrupen per la seva forma.
            # No ens importa quina peça no objectiu es mou, només on està.
            shape_key = ("NORMAL", piece.coords)
        
        if shape_key not in groups:
            groups[shape_key] = []
        groups[shape_key].append(estat.positions[i])
        
    # Ordenem les posicions de cada grup i construïm la clau
    canonical_parts = []
    for shape in sorted(groups.keys(), key=str):
        canonical_parts.append((shape, tuple(sorted(groups[shape]))))
        
    return tuple(canonical_parts)
 

def _a_star_real(pz: Puzzle, max_estats: Optional[int] = None) -> Optional[list]:
    """
    Executa l'algorisme de cerca A* (A-Estrella) sobre l'espai d'estats reals 
    utilitzant la clau canònica híbrida per a la memòria de visitats.
    
    Pre: 'pz' és un Puzzle vàlid. 'max_estats' pot limitar la quantitat de nodes a explorar.
    Post: Retorna una llista de moviments (camí òptim) per resoldre el puzzle. 
          Cada moviment és una llista [índex_peça, direcció, distància]. 
          Retorna None si el puzzle no té solució o s'excedeix 'max_estats'.
    """
    estat_inicial = pz.start
 
    if is_goal(pz, estat_inicial):
        return []
 
    cua = []
    counter = itertools.count() 
    
    g_score = 0
    h_score = heuristica(pz, estat_inicial)
    
    heapq.heappush(cua, (g_score + h_score, next(counter), g_score, estat_inicial, []))
 
    # Utilitzem la clau canònica híbrida per a guardar les distàncies
    clau_inicial = canonical_key(pz, estat_inicial)
    distancies = {clau_inicial: 0}
 
    estats_explorats = 0
 
    while cua:
        estats_explorats += 1
        if max_estats is not None and estats_explorats > max_estats:
            return None
            
        f, _, g, estat, cami = heapq.heappop(cua)
 
        if is_goal(pz, estat):
            return cami
            
        clau_actual = canonical_key(pz, estat)
        if g > distancies.get(clau_actual, float('inf')):
            continue
 
        for move in possible_moves(pz, estat):
            nou_estat = apply_move(pz, estat, move)
            nou_g = g + 1
            
            # Canonicalitzem l'estat fill
            pos_key = canonical_key(pz, nou_estat)
            
            if nou_g < distancies.get(pos_key, float('inf')):
                distancies[pos_key] = nou_g
                nou_f = nou_g + heuristica(pz, nou_estat)
                
                p_idx, direction, dist = move
                nou_cami = cami + [[p_idx, direction, dist]]
                heapq.heappush(cua, (nou_f, next(counter), nou_g, nou_estat, nou_cami))
 
    return None
 
 
def solucio_puzzle(pz: Puzzle, output_path: Path) -> None:
    """
    Calcula i desa la solució final d'un puzzle en un fitxer JSON.
    
    Pre: 'pz' és un puzzle resoluble i 'output_path' és una ruta d'arxiu vàlida.
    Post: S'escriu un array JSON a 'output_path' que conté l'ordre de moviments 
          per arribar a la victòria. Llança una asserció si el puzzle no té solució.
    """
    solucio_final = _a_star_real(pz)
    assert solucio_final is not None, "El puzzle és resoluble però l'A* no ha trobat solució"
 
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