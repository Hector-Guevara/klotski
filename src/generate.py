"""
Genera un nou puzzle en format .json en base a un nivell de dificultat.

Aquesta versió clona l'estructura matemàtica dels puzles Top-Tier (4.5+ estrelles):
- Taulells de 5x6 o 6x5.
- SENSE parets (les parets fracturen el graf inútilment).
- Densitat mil·limètrica (deixant entre 3 i 5 caselles lliures).
- Ús de formes complexes (L, T, Z) combinades amb peces petites.
- Generació Forward: Col·loca la peça més gran i l'envia a la cantonada oposada.
"""

from __future__ import annotations

import random
import sys
from dataclasses import dataclass
from pathlib import Path

from puzzle import Puzzle, Piece, State
from eval import avaluar_puzzle, imprimir_avaluacio
from logic import possible_moves

# ---------------------------------------------------------------------------
# Catàleg de formes complet
# ---------------------------------------------------------------------------

FORMES_CATALEG: list[list[tuple[int, int]]] = [
    [(0, 0)], [(0, 0), (1, 0)], [(0, 0), (0, 1)],
    [(0, 0), (1, 0), (2, 0)], [(0, 0), (0, 1), (0, 2)],
    [(0, 0), (0, 1), (1, 0)], [(0, 0), (1, 0), (1, 1)],
    [(0, 1), (1, 0), (1, 1)], [(0, 0), (0, 1), (1, 1)],
    [(0, 0), (0, 1), (1, 0), (1, 1)],
    [(0, 0), (1, 0), (2, 0), (3, 0)], [(0, 0), (0, 1), (0, 2), (0, 3)],
    [(0, 0), (1, 0), (2, 0), (1, 1)], [(0, 0), (0, 1), (0, 2), (1, 1)],
    [(0, 1), (1, 0), (1, 1), (2, 1)], [(0, 1), (1, 0), (1, 1), (1, 2)],
    [(0, 0), (0, 1), (0, 2), (1, 2)], [(0, 0), (1, 0), (2, 0), (2, 1)],
    [(0, 0), (1, 0), (1, 1), (1, 2)], [(0, 1), (1, 1), (2, 0), (2, 1)],
    [(0, 0), (0, 1), (0, 2), (1, 0)], [(0, 0), (1, 0), (2, 0), (0, 1)],
    [(0, 2), (1, 0), (1, 1), (1, 2)], [(0, 0), (0, 1), (1, 1), (2, 1)],
    [(0, 1), (1, 0), (1, 1), (2, 0)], [(0, 0), (0, 1), (1, 1), (1, 2)],
    [(0, 0), (1, 0), (1, 1), (2, 1)], [(0, 1), (0, 2), (1, 0), (1, 1)],
]

_FALLBACKS = [[(0, 0), (0, 1)], [(0, 0), (1, 0)], [(0, 0)]]

# ---------------------------------------------------------------------------
# Configuració dels nivells de dificultat
# ---------------------------------------------------------------------------

@dataclass
class NivellConfig:
    dimensions: list[tuple[int, int]]
    ocupacio: float
    pesos_mida: dict[int, int]
    amb_parets: bool
    nombre_objectius: int
    puntuacio_minima: float
    max_intents: int

NIVELLS: dict[str, NivellConfig] = {
    "easy": NivellConfig(
        dimensions=[(4, 4), (4, 5)], ocupacio=0.65,
        pesos_mida={1: 5, 2: 4, 3: 1, 4: 0}, amb_parets=False,
        nombre_objectius=1, puntuacio_minima=1.0, max_intents=30,
    ),
    "medium": NivellConfig(
        dimensions=[(5, 5)], ocupacio=0.80,
        pesos_mida={1: 4, 2: 5, 3: 3, 4: 1}, amb_parets=False,
        nombre_objectius=1, puntuacio_minima=2.0, max_intents=60,
    ),
    "hard": NivellConfig(
        dimensions=[(5, 6), (6, 5)], 
        ocupacio=0.86, # 26 caselles ocupades de 30 = exactament 4 forats lliures
        pesos_mida={1: 3, 2: 6, 3: 4, 4: 3}, # La Proporció Àuria (poquets 1x1, molts dòminos, algunes complexes)
        amb_parets=False, # SENSE PARETS
        nombre_objectius=1, # 1 sol objectiu maximitza la unicitat de la solució
        puntuacio_minima=3.6, 
        max_intents=150, 
    ),
}

# ---------------------------------------------------------------------------
# Funcions auxiliars
# ---------------------------------------------------------------------------

def _forma_ponderada(pesos_mida: dict[int, int]) -> list[tuple[int, int]]:
    formes_valides = [f for f in FORMES_CATALEG if pesos_mida.get(len(f), 0) > 0]
    pesos = [pesos_mida.get(len(f), 0) for f in formes_valides]
    return random.choices(formes_valides, weights=pesos, k=1)[0]

def _trobar_objectiu_lluny(
    peça: Piece, pos_actual: tuple[int, int], ocupades: set[tuple[int, int]], W: int, H: int
) -> tuple[int, int] | None:
    max_dx = max(dx for dx, _ in peça.coords)
    max_dy = max(dy for _, dy in peça.coords)

    opcions = []
    for gx in range(W - max_dx):
        for gy in range(H - max_dy):
            if (gx, gy) == pos_actual:
                continue
            dist = abs(gx - pos_actual[0]) + abs(gy - pos_actual[1])
            opcions.append((dist, (gx, gy)))

    if not opcions:
        return None

    opcions.sort(reverse=True)
    # Ens quedem amb la posició absolutament més llunyana possible (cantonada oposada normalment)
    return opcions[0][1]

# ---------------------------------------------------------------------------
# Generació principal del puzzle (FORWARD GENERATION)
# ---------------------------------------------------------------------------

def generar_puzzle(cfg: NivellConfig) -> Puzzle | None:
    W, H = random.choice(cfg.dimensions)

    ocupades: set[tuple[int, int]] = set()
    area_total = W * H
    area_max = int(area_total * cfg.ocupacio)

    peces_generades: list[Piece] = []
    posicions_inicials: list[tuple[int, int]] = []
    area_actual = 0
    intents = 0

    # Assegurem posar almenys una peça grossa (mida 4) al principi per fer de Meta
    formes_grans = [f for f in FORMES_CATALEG if len(f) == 4]
    forma_inicial = random.choice(formes_grans)
    
    # Bucle d'ompliment
    while area_actual < area_max and intents < 200:
        intents += 1
        
        if area_actual == 0:
            forma_coords = forma_inicial
        else:
            forma_coords = _forma_ponderada(cfg.pesos_mida)
            
        pos = None
        for candidata in [forma_coords] + _FALLBACKS:
            if area_actual + len(candidata) > area_max: continue
            max_dx = max(dx for dx, _ in candidata)
            max_dy = max(dy for _, dy in candidata)
            candidats = [
                (px, py) for px in range(W - max_dx) for py in range(H - max_dy)
                if all((px + dx, py + dy) not in ocupades for dx, dy in candidata)
            ]
            if candidats:
                pos = random.choice(candidats)
                forma_coords = candidata
                break

        if pos:
            px, py = pos
            peça = Piece.normalized(forma_coords)
            peces_generades.append(peça)
            posicions_inicials.append((px, py))
            for dx, dy in forma_coords:
                ocupades.add((px + dx, py + dy))
            area_actual += len(forma_coords)

    if not peces_generades: return None

    # Ordenació canònica de sortida
    pairs = sorted(zip(peces_generades, posicions_inicials))
    peces_final = tuple(p for p, _ in pairs)
    posicions_final = tuple(pos for _, pos in pairs)

    # Identificar la peça més gran per fer-la objectiu
    idx_meta = max(range(len(peces_final)), key=lambda i: len(peces_final[i].coords))
    
    pos_meta = _trobar_objectiu_lluny(peces_final[idx_meta], posicions_final[idx_meta], set(), W, H)
    if pos_meta is None:
        return None

    goals = ((idx_meta, pos_meta),)

    return Puzzle(
        W=W, H=H, walls=(), pieces=peces_final, start=State(posicions_final), goals=goals
    )

# ---------------------------------------------------------------------------
# Cerca del millor puzzle
# ---------------------------------------------------------------------------

def generar_millor_puzzle(cfg: NivellConfig, nivell: str) -> tuple[Puzzle, dict]:
    millor_puzzle: Puzzle | None = None
    millor_resultat: dict = {"puntuacio": -1.0}

    for intent in range(1, cfg.max_intents + 1):
        print(f"  → Intent {intent:3d}/{cfg.max_intents}: Generant... ", end="", flush=True)
        
        pz = generar_puzzle(cfg)
        if pz is None:
            print("❌ Ignorat (Sense espai)")
            continue
            
        if not possible_moves(pz, pz.start):
            print("❌ Ignorat (Bloquejat d'inici)")
            continue

        print("Avaluant... ", end="", flush=True)
        try:
            resultat = avaluar_puzzle(pz)
        except Exception as e:
            print(f"❌ Error d'avaluació ({e})")
            continue

        if not resultat["resoluble"]:
            print(f"⚠️  No resoluble")
            continue

        print(f"✅ RESOLUBLE! ({resultat['num_estats']} estats) — Nota: {resultat['puntuacio']:.2f}")

        if resultat["puntuacio"] > millor_resultat["puntuacio"]:
            millor_puzzle = pz
            millor_resultat = resultat

        if millor_resultat["puntuacio"] >= cfg.puntuacio_minima:
            print(f"\n  ✓ Puntuació objectiu assolida!")
            break

    if millor_puzzle is None:
        print(f"\nError: no s'ha pogut generar cap puzzle '{nivell}' resoluble.")
        sys.exit(1)

    return millor_puzzle, millor_resultat

if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(1)

    nivell = sys.argv[1].lower()
    nom_arxiu = sys.argv[2]
    
    if nivell not in NIVELLS:
        print(f"Error: nivell '{nivell}' desconegut. Usa 'easy', 'medium' o 'hard'.")
        sys.exit(1)
        
    cfg = NIVELLS[nivell]

    print(f"Generant puzzle '{nom_arxiu}' [nivell: {nivell.upper()}]...")
    millor, resultat = generar_millor_puzzle(cfg, nivell)

    path = Path(f"{nom_arxiu}.json")
    path.write_text(millor.to_json(indent=4))

    print(f"\nMillor puzzle guardat a '{path}'")
    imprimir_avaluacio(millor, resultat)