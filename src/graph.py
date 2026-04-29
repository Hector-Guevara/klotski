"""
Donat un puzzle, genera el graf resultant en un fitxer .graphml

Ús: python3 graph.py <puzzle.json>
"""

from __future__ import annotations

import sys
from pathlib import Path
from puzzle import Puzzle, State
from typing import Dict, List, Tuple
from collections import defaultdict
from logic import possible_moves, apply_move

import graph_tool.all as gt  # type: ignore[import-untyped]

StateKey = str

def state_key(puzzle: Puzzle, estat: State) -> StateKey:
    """
    Donat un puzzle, i l'estat d'aquest taulell del puzzle, genera una clau única, en format
    de StateKey per dotar d'una identificació única a cada estat del taulell.
    """

    # Creamos un diccionario para agrupar posiciones según la forma de la pieza.
    # - Clave: La forma de la pieza (una tupla de coordenadas relativas)
    # - Valor: Una lista con las posiciones (x, y) absolutas en el tablero
    groups: Dict[Tuple[Tuple[int, int], ...], List[Tuple[int, int]]] = defaultdict(list)
    
    # 1. Agrupamos dónde está cada pieza basándonos en su forma geométrica
    for i, piece in enumerate(puzzle.pieces):
        # piece.coords es la forma estática (ej: un cuadrado de 1x1)
        # state.positions[i] es dónde está puesto ese cuadrado ahora mismo
        groups[piece.coords].append(estat.positions[i])
        
    canonical_parts = []
    
    # 2. Ordenamos todo para que el resultado sea siempre determinista
    # Primero iteramos las formas de las piezas en un orden fijo:
    for shape in sorted(groups.keys()):
        # Luego ordenamos las posiciones de todas las piezas que tienen esa forma:
        sorted_positions = tuple(sorted(groups[shape]))
        canonical_parts.append((shape, sorted_positions))
        
    # 3. Lo convertimos a una tupla de tuplas y luego a texto (string)
    return str(tuple(canonical_parts))

def generar_graf(puzzle: Puzzle) -> gt.Graph:
    """
    Donat un puzzle, en retorna el seu graf associat, que defineix la resolució
    d'aquest puzzle. Els nodes del graf són els possibles estats i posicions de les peces,
    si una aresta els uneix, implica que es pot anar d'un estat a un altre en un sol moviment.
    El graf que retorna la funció és en l'extensió .graphml.
    """

    # 1. Creamos el objeto Grafo (dirigido, porque los movimientos tienen sentido)
    g = gt.Graph(directed=True)

    # 2. Creamos la propiedad "state" en los vértices. 
    # Esto es OBLIGATORIO para que 3D_view.py pueda leer el archivo .graphml
    v_state = g.new_vertex_property("string")
    g.vp["state"] = v_state

    # 3. Diccionario auxiliar para no repetir nodos
    # Clave: la huella de texto (StateKey) -> Valor: el objeto vértice de graph-tool
    visited = {}

    # 4. Inicializamos la exploración con el estado inicial del puzzle
    start_state = puzzle.start
    start_key = state_key(puzzle, start_state)
    
    # Creamos el primer nodo
    v_start = g.add_vertex()
    g.vp["state"][v_start] = start_key
    visited[start_key] = v_start

    # Usamos una lista como "pila" (Stack) para hacer una exploración DFS
    stack = [start_state]

    print(f"Empezando exploración...")

    # 5. Bucle principal de exploración
    while stack:
        current_state = stack.pop()
        current_key = state_key(puzzle, current_state)
        v_current = visited[current_key]

        # Probamos todos los movimientos posibles desde el estado actual
        for move in possible_moves(puzzle, current_state):
            # Calculamos cómo quedaría el tablero tras el movimiento
            next_state = apply_move(puzzle, current_state, move)
            next_key = state_key(puzzle, next_state)

            # Si este estado es nuevo para nosotros...
            if next_key not in visited:
                # Creamos un nuevo vértice en el grafo
                v_next = g.add_vertex()
                # Le pegamos su "etiqueta" de estado
                g.vp["state"][v_next] = next_key
                # Lo registramos como visitado
                visited[next_key] = v_next
                # Lo añadimos a la pila para explorar sus hijos más tarde
                stack.append(next_state)
            
            # Independientemente de si el nodo es nuevo o no, 
            # añadimos la arista (el camino) entre el actual y el siguiente
            g.add_edge(v_current, visited[next_key])

    print(f"Exploración finalizada.")
    print(f"Nodos totales: {g.num_vertices()}")
    print(f"Aristas totales: {g.num_edges()}")
    
    return g
    

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Ús: python3 {sys.argv[0]} <puzzle.json>")
        sys.exit(1)

    json_path = Path(sys.argv[1])
    pz = Puzzle.from_json(json_path.read_text())
    g = generar_graf(pz)

    output_filename = sys.argv[1].replace('.json', '.graphml')
    g.save(output_filename)
    print(f"Graf guardat a {output_filename}")