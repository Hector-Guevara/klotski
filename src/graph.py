"""
Donat un puzzle, genera el graf resultant en un fitxer .graphml

Ús: python3 graph.py <puzzle.json>
"""

from __future__ import annotations

import sys
from pathlib import Path
from puzzle import Puzzle, State
from logic import possible_moves, apply_move

import graph_tool.all as gt  # type: ignore[import-untyped]

StateKey = str

def state_key(puzzle: Puzzle, estat: State) -> StateKey:
    """
    Donat un puzzle, i l'estat d'aquest taulell del puzzle, genera una clau única, en format
    de StateKey per dotar d'una identificació única a cada estat del taulell.
    """
    # inicialització de la variable
    groups: dict[tuple[tuple[int, int], ...], list[tuple[int, int]]] = {}
    
    # es guarda la posició de cada peça segons la forma
    for i, piece in enumerate(puzzle.pieces):

        if piece.coords not in groups:
            groups[piece.coords] = []
            
        # es guarden les posicions de la peça
        groups[piece.coords].append(estat.positions[i])
        
    canonical_parts = []
    
    # s'itera sobre les peces en ordre
    for shape in sorted(groups.keys()):
        # s'ordenen les posicions de cada peça
        sorted_positions = tuple(sorted(groups[shape]))
        canonical_parts.append((shape, sorted_positions))
        
    # es retorna com a text
    return str(tuple(canonical_parts))

def generar_graf(puzzle: Puzzle) -> gt.Graph:
    """
    Donat un puzzle, en retorna el seu graf associat, que defineix la resolució
    d'aquest puzzle. Els nodes del graf són els possibles estats i posicions de les peces,
    si una aresta els uneix, implica que es pot anar d'un estat a un altre en un sol moviment.
    El graf que retorna la funció és en l'extensió .graphml.
    """

    # es crea el graf dirigit amb l'eina aportada per graph-tool
    g = gt.Graph(directed=True)

    v_state = g.new_vertex_property("string")
    g.vp["state"] = v_state

    # diccionari auxiliar per no repetir nodes
    # Clave: la huella de texto (StateKey) -> Valor: el objeto vértice de graph-tool
    visited: dict[StateKey, gt.Vertex] = {}

    # s'inicialitza l'exploració amb l'estat inicial del puzzle
    start_state = puzzle.start
    start_key = state_key(puzzle, start_state)
    
    # es crea el primer node
    v_start = g.add_vertex()
    g.vp["state"][v_start] = start_key
    visited[start_key] = v_start

    # es crea una pila per inicialitzar un algorisme DFS
    stack = [start_state]

    print(f"Empezando exploración...")

    # DFS
    while stack:
        current_state = stack.pop()
        current_key = state_key(puzzle, current_state)
        v_current = visited[current_key]

        # es comproven els possibles moviments
        for move in possible_moves(puzzle, current_state):
            next_state = apply_move(puzzle, current_state, move)
            next_key = state_key(puzzle, next_state)

            if next_key not in visited:
                v_next = g.add_vertex()
                g.vp["state"][v_next] = next_key
                visited[next_key] = v_next
                stack.append(next_state)
            
            # encara que no es visiti després, sempre cal afegir l'aresta entre els dos nodes
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