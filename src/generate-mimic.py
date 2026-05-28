"""
Genera un puzzle competitiu per a DOS JUGADORS aprofitant el motor de generate.py.

Estratègia:
1. Delega en `generar_millor_puzzle` de generate.py per obtenir una base excel·lent.
2. Clona exactament les mateixes peces i objectius desplaçant-los cap avall.
3. Insereix una fila central plena de barreres (parets) per aïllar els dos jugadors.

Ús: python3 generate-two-player.py <easy|medium|hard> <nom_puzzle>
"""

from __future__ import annotations

import sys
import json
from pathlib import Path

from puzzle import Puzzle, State
# IMPORTACIÓ MESTRA: Aprofitem la lògica pesada que ja tenim!
from generate import generar_millor_puzzle, NIVELLS


def convertir_a_dos_jugadors(base_pz: Puzzle) -> Puzzle:
    W = base_pz.W
    H = base_pz.H
    N = len(base_pz.pieces)
    
    nou_W = W
    nou_H = (H * 2) + 1  # Dos taulells + 1 fila al mig per la paret
    
    # 1. Crear les parets que divideixen el taulell just al mig
    noves_parets = [(x, H) for x in range(W)]
    
    totes_peces = []
    totes_posicions = []
    
    # 2. Jugador 1 (Meitat de Dalt)
    for i in range(N):
        totes_peces.append(base_pz.pieces[i])
        totes_posicions.append(base_pz.start.positions[i])
        
    # 3. Jugador 2 (Meitat de Baix) - Desplaçat H + 1 cap a baix
    for i in range(N):
        totes_peces.append(base_pz.pieces[i])
        x, y = base_pz.start.positions[i]
        totes_posicions.append((x, y + H + 1))
        
    # 4. Mantenir l'ordre canònic estricte per no trencar puzzle.py
    items = list(zip(totes_peces, totes_posicions, range(2 * N)))
    items.sort(key=lambda x: (x[0], x[1]))
    
    peces_finals = tuple(x[0] for x in items)
    posicions_finals = tuple(x[1] for x in items)
    antic_a_nou_idx = {x[2]: i for i, x in enumerate(items)}
    
    # 5. Duplicar objectius
    nous_objectius = []
    for antic_idx, (gx, gy) in base_pz.goals:
        # Objectiu Jugador 1
        nous_objectius.append((antic_a_nou_idx[antic_idx], (gx, gy)))
        # Objectiu Jugador 2
        nous_objectius.append((antic_a_nou_idx[antic_idx + N], (gx, gy + H + 1)))
        
    nous_objectius = tuple(sorted(nous_objectius))
    
    return Puzzle(
        W=nou_W, H=nou_H, walls=tuple(sorted(noves_parets)),
        pieces=peces_finals, start=State(posicions_finals), goals=nous_objectius
    )


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Ús: python3 {sys.argv[0]} <easy|medium|hard> <nom_puzzle>")
        sys.exit(1)

    nivell = sys.argv[1].lower()
    nom_arxiu = sys.argv[2]
    
    if nivell not in NIVELLS:
        print(f"Error: nivell '{nivell}' desconegut. Usa 'easy', 'medium' o 'hard'.")
        sys.exit(1)

    print(f"== GENERANT PUZZLE VERSUS (2 JUGADORS) ==")
    print("Fase 1: Buscant un taulell base perfecte...")
    
    cfg = NIVELLS[nivell]
    # Cridem al motor de generate.py
    millor_base, resultat = generar_millor_puzzle(cfg, nivell)

    print("\nFase 2: Clonant el taulell i afegint la paret central...")
    puzzle_2p = convertir_a_dos_jugadors(millor_base)

    path = Path(f"{nom_arxiu}.json")
    path.write_text(puzzle_2p.to_json(indent=4))

    print(f"🎉 Puzzle Versus guardat a '{path}'")
    print(f"Taulell competitiu creat: {puzzle_2p.W}x{puzzle_2p.H} amb {len(puzzle_2p.pieces)} peces en total.")
    print("Obre'l al 3D_view.py per veure la pista doble!")