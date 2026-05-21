"""
Donat un puzzle, genera el graf resultant en un fitxer .graphml
de forma ultra ràpida mitjançant add_edge_list.

Ús: python3 graph.py <puzzle.json>
"""

from __future__ import annotations

import sys
from pathlib import Path
from puzzle import Puzzle, State
from logic import possible_moves, apply_move, is_goal
from solve import canonical_key  # Aprofitem la clau ràpida que ja tenim!

import graph_tool.all as gt  # type: ignore[import-untyped]

StateKey = str

def state_key(puzzle: Puzzle, estat: State | StateKey) -> StateKey:
    """
    Manté la compatibilitat per a funcions externes que esperen un string,
    però utilitzant la lògica ràpida de canonical_key.
    """
    if isinstance(estat, str):
        return estat
    return str(canonical_key(puzzle, estat))


def generar_graf(puzzle: Puzzle, limit_estats: int | None = None) -> tuple[gt.Graph, list[gt.Vertex]]:
    """
    Genera el graf del puzzle processant la cerca purament en Python
    i construint el graf de graph-tool en bloc per a màxima velocitat.
    Si s'indica limit_estats, la cerca es talla un cop superat aquest límit d'estats
    per evitar col·lapsar la memòria en puzles gegants.
    """
    start_state = puzzle.start
    start_key = canonical_key(puzzle, start_state)
    
    visited_idx: dict[tuple, int] = {start_key: 0}
    
    state_strings: list[str] = [str(start_key)]
    is_goal_list: list[bool] = [is_goal(puzzle, start_state)]
    is_start_list: list[bool] = [True]
    
    edges: list[tuple[int, int]] = []
    stack = [start_state]

    while stack:
        # TALLAFOCS OPCIONAL: Tallem l'exploració si el graf es descontrola
        if limit_estats is not None and len(visited_idx) >= limit_estats:
            break

        estat_actual = stack.pop()
        current_key = canonical_key(puzzle, estat_actual)
        curr_idx = visited_idx[current_key]

        for move in possible_moves(puzzle, estat_actual):
            next_state = apply_move(puzzle, estat_actual, move)
            next_key = canonical_key(puzzle, next_state)

            if next_key not in visited_idx:
                nou_idx = len(visited_idx)
                visited_idx[next_key] = nou_idx
                
                state_strings.append(str(next_key))
                is_goal_list.append(is_goal(puzzle, next_state))
                is_start_list.append(False)
                
                stack.append(next_state)
            
            edges.append((curr_idx, visited_idx[next_key]))

    # Construcció del graf en bloc (molt més ràpid)
    g = gt.Graph(directed=True)
    g.add_vertex(len(visited_idx))
    g.add_edge_list(edges)

    # Assignació de propietats
    v_is_goal = g.new_vertex_property("bool")
    v_is_start = g.new_vertex_property("bool")
    v_state = g.new_vertex_property("string") 
    
    v_is_goal.a = is_goal_list
    v_is_start.a = is_start_list
    
    for i, s_str in enumerate(state_strings):
        v_state[g.vertex(i)] = s_str

    g.vp["is_goal"] = v_is_goal
    g.vp["is_start"] = v_is_start
    g.vp["state"] = v_state
    
    g.graph_properties["puzzle"] = g.new_graph_property("string")
    g.graph_properties["puzzle"] = puzzle.to_json()

    # Localitzem els nodes destí per retornar-los
    nodes_desti = [g.vertex(i) for i, is_g in enumerate(is_goal_list) if is_g]
    
    return g, nodes_desti


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Ús: python3 {sys.argv[0]} <puzzle.json>")
        sys.exit(1)

    json_path = Path(sys.argv[1])
    pz = Puzzle.from_json(json_path.read_text())
    
    # Executat manualment NO té límit, genera el 100% per al visualitzador 3D
    g, destins = generar_graf(pz)

    output_filename = sys.argv[1].replace('.json', '.graphml')
    g.save(output_filename)
    print(f"Graf complet guardat a {output_filename} (Nodes: {g.num_vertices()}, Arestes: {g.num_edges()})")