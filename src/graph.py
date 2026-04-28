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

from dataclasses import dataclass

@dataclass

class StateKey:
    ...

def state_key() -> ...:
    ...

def generar_graf(puzzle: Puzzle) -> gt.Graph:
    """
    Donat un puzzle, en retorna el seu graf associat, que defineix la resolució
    d'aquest puzzle. Els nodes del graf són els possibles estats i posicions de les peces,
    si una aresta els uneix, implica que es pot anar d'un estat a un altre en un sol moviment.
    El graf que retorna la funció és en l'extensió .graphml.
    """

    ...
    

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