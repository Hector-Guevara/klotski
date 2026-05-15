"""
Donat un puzzle, genera el graf resultant en un fitxer .graphml

Ús: python3 graph.py <puzzle.json>
"""

from __future__ import annotations

import sys
from pathlib import Path
from puzzle import Puzzle, State
from logic import possible_moves, apply_move, is_goal

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

        shape_key = tuple(tuple(c) for c in piece.coords)

        if shape_key not in groups:
            groups[shape_key] = []
            
        # es guarden les posicions de la peça
        groups[shape_key].append((tuple(estat.positions[i])))
        
    canonical_parts = []
    
    # s'itera sobre les peces en ordre
    for shape in sorted(groups.keys()):
        # s'ordenen les peces per posició
        sorted_positions = tuple(sorted(groups[shape]))
        canonical_parts.append((shape, sorted_positions))
        
    # es retorna com a text
    return str(tuple(canonical_parts))

def generar_graf(puzzle: Puzzle) -> tuple[gt.Graph, list[gt.Vertex]]:
    """
    Donat un puzzle, en retorna el seu graf associat, que defineix la resolució
    d'aquest puzzle i la llista amb tots els nodes que són part de la solució. 
    Els nodes del graf són els possibles estats i posicions de les peces,
    si una aresta els uneix, implica que es pot anar d'un estat a un altre en un sol moviment.
    """
        
    # 1. Creació del graf
    g = gt.Graph(directed=True)

    # 2. Definició de propietats exactes segons 2swapog.graphml
    v_is_goal = g.new_vertex_property("bool")
    v_is_start = g.new_vertex_property("bool")
    v_state = g.new_vertex_property("object") 
    
    g.vp["is_goal"] = v_is_goal
    g.vp["is_start"] = v_is_start
    g.vp["state"] = v_state
    
    g.graph_properties["puzzle"] = g.new_graph_property("string")
    g.graph_properties["puzzle"] = puzzle.to_json()

    visited: dict[StateKey, gt.Vertex] = {}
    nodes_desti: list[gt.Vertex] = []

    start_state = puzzle.start
    start_key = state_key(puzzle, start_state)
    
    v_inicial = g.add_vertex()
    g.vp["state"][v_inicial] = start_key
    g.vp["is_start"][v_inicial] = True
    g.vp["is_goal"][v_inicial] = is_goal(puzzle, start_state)
    visited[start_key] = v_inicial

    stack = [start_state]

    while stack:
        estat_actual = stack.pop()
        current_key = state_key(puzzle, estat_actual)
        v_actual = visited[current_key]

        if is_goal(puzzle, estat_actual) and v_actual not in nodes_desti:
            g.vp["is_goal"][v_actual] = True
            nodes_desti.append(v_actual)

        for move in possible_moves(puzzle, estat_actual):
            next_state = apply_move(puzzle, estat_actual, move)
            next_key = state_key(puzzle, next_state)

            if next_key not in visited:
                v_next = g.add_vertex()
                g.vp["state"][v_next] = next_key
                g.vp["is_start"][v_next] = False
                g.vp["is_goal"][v_next] = is_goal(puzzle, next_state)
                visited[next_key] = v_next
                stack.append(next_state)
            
            g.add_edge(v_actual, visited[next_key])
    
    return g, nodes_desti

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Ús: python3 {sys.argv[0]} <puzzle.json>")
        sys.exit(1)

    json_path = Path(sys.argv[1])
    pz = Puzzle.from_json(json_path.read_text())
    g, destins = generar_graf(pz)

    output_filename = sys.argv[1].replace('.json', '.graphml')
    g.save(output_filename)
    print(f"Graf guardat a {output_filename}")