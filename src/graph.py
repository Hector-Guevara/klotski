"""
Donat un puzzle, genera el graf resultant en un fitxer .graphml
de forma ultra ràpida mitjançant add_edge_list.

Ús: python3 graph.py <puzzle.json>
"""

from __future__ import annotations

import sys
from pathlib import Path
from array import array

from puzzle import Puzzle, State
from logic import possible_moves, apply_move, is_goal
from solve import canonical_key

import graph_tool.all as gt  # type: ignore[import-untyped]

StateKey = str


def state_key(puzzle: Puzzle, estat: State | StateKey) -> StateKey:
    """
    Manté compatibilitat amb funcions externes esperant string,
    però reutilitzant canonical_key.
    """
    if isinstance(estat, str):
        return estat
    return str(canonical_key(puzzle, estat))


def generar_graf(
    puzzle: Puzzle,
    limit_estats: int | None = None
) -> tuple[gt.Graph, list[gt.Vertex]]:
    """
    Genera el graf del puzzle processant la cerca en Python
    i construint el graf de graph-tool en bloc.

    Si s'indica limit_estats, talla l'exploració per evitar
    col·lapse de memòria en puzles gegants.
    """

    start_state = puzzle.start
    start_key = canonical_key(puzzle, start_state)

    # visited: state_key -> vertex_index
    visited_idx: dict[tuple, int] = {start_key: 0}

    # propietats de node
    state_strings: list[str] = [str(start_key)]
    is_goal_list: list[bool] = [is_goal(puzzle, start_state)]
    is_start_list: list[bool] = [True]

    # arestes compactes
    edges_src = array("I")
    edges_dst = array("I")

    # DFS iteratiu
    stack: list[State] = [start_state]

    # cache locals (més ràpid dins del loop)
    possible = possible_moves
    apply = apply_move
    canon = canonical_key
    goal = is_goal

    visited_get = visited_idx.get
    visited_set = visited_idx.__setitem__

    append_src = edges_src.append
    append_dst = edges_dst.append

    stack_append = stack.append
    stack_pop = stack.pop

    while stack:

        # limit opcional
        if (
            limit_estats is not None
            and len(visited_idx) >= limit_estats
        ):
            break

        estat_actual = stack_pop()

        current_key = canon(puzzle, estat_actual)
        curr_idx = visited_idx[current_key]

        for move in possible(puzzle, estat_actual):

            next_state = apply(puzzle, estat_actual, move)
            next_key = canon(puzzle, next_state)

            idx = visited_get(next_key)

            if idx is None:
                idx = len(visited_idx)

                visited_set(next_key, idx)

                state_strings.append(str(next_key))
                is_goal_list.append(goal(puzzle, next_state))
                is_start_list.append(False)

                stack_append(next_state)

            append_src(curr_idx)
            append_dst(idx)

    # construir graf en bloc
    g = gt.Graph(directed=True)
    g.add_vertex(len(visited_idx))

    # graph-tool accepta iterable de parelles
    g.add_edge_list(zip(edges_src, edges_dst))

    # propietats
    v_is_goal = g.new_vertex_property("bool")
    v_is_start = g.new_vertex_property("bool")
    v_state = g.new_vertex_property("string")

    v_is_goal.a = is_goal_list
    v_is_start.a = is_start_list

    # string property map
    for i, s in enumerate(state_strings):
        v_state[g.vertex(i)] = s

    g.vp["is_goal"] = v_is_goal
    g.vp["is_start"] = v_is_start
    g.vp["state"] = v_state

    # metadades del puzzle
    g.graph_properties["puzzle"] = g.new_graph_property("string")
    g.graph_properties["puzzle"] = puzzle.to_json()

    # nodes objectiu
    nodes_desti = [
        g.vertex(i)
        for i, is_g in enumerate(is_goal_list)
        if is_g
    ]

    return g, nodes_desti


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print(f"Ús: python3 {sys.argv[0]} <puzzle.json>")
        sys.exit(1)

    json_path = Path(sys.argv[1])

    pz = Puzzle.from_json(json_path.read_text())

    # sense límit → graf complet
    g, destins = generar_graf(pz)

    output_filename = sys.argv[1].replace(".json", ".graphml")

    g.save(output_filename)

    print(
        f"Graf complet guardat a {output_filename} "
        f"(Nodes: {g.num_vertices()}, "
        f"Arestes: {g.num_edges()})"
    )