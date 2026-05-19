"""
Genera un nou puzzle en format .json en base a un nivell de dificultat.

El programa escull automàticament les dimensions del taulell, el nombre de
peces, la seva mida, les parets i el nombre d'objectius per maximitzar la
dificultat del nivell demanat.

Ús: python3 generate.py <easy|medium|hard> <nom_puzzle>

Nivells:
  easy   — taulell petit, poques peces petites, molt espai lliure, 1 objectiu
  medium — taulell mitjà, peces mixtes, densitat moderada, 1 objectiu
  hard   — taulell gran, moltes peces grans, taulell molt dens, parets, 1 objectiu

Estratègia anti-bloqueig:
  - Els paràmetres de cada nivell estan calibrats per garantir que la majoria
    de puzzles generats siguin resolubles sense necessitar massa intents.
  - Per a 'hard', les dimensions del taulell es trien aleatòriament dins d'un
    rang que garanteix prou espai lliure perquè les peces es puguin moure.
  - Si en MAX_INTENTS intents no es troba cap puzzle resoluble, el programa
    retorna el millor que hagi trobat (encara que no assoleixi PUNTUACIO_MINIMA).
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
# Catàleg de formes: totes les orientacions de poliominós fins a mida 4
# ---------------------------------------------------------------------------

FORMES_CATALEG: list[list[tuple[int, int]]] = [
    # Dòminos (mida 2)
    [(0, 0), (1, 0)],
    [(0, 0), (0, 1)],
    # Triòminós I (mida 3)
    [(0, 0), (1, 0), (2, 0)],
    [(0, 0), (0, 1), (0, 2)],
    # Triòminós L (mida 3)
    [(0, 0), (0, 1), (1, 0)],
    [(0, 0), (1, 0), (1, 1)],
    [(0, 1), (1, 0), (1, 1)],
    [(0, 0), (0, 1), (1, 1)],
    # Tetròminós O (mida 4)
    [(0, 0), (0, 1), (1, 0), (1, 1)],
    # Tetròminós I (mida 4)
    [(0, 0), (1, 0), (2, 0), (3, 0)],
    [(0, 0), (0, 1), (0, 2), (0, 3)],
    # Tetròminós T (mida 4)
    [(0, 0), (1, 0), (2, 0), (1, 1)],
    [(0, 0), (0, 1), (0, 2), (1, 1)],
    [(0, 1), (1, 0), (1, 1), (2, 1)],
    [(0, 1), (1, 0), (1, 1), (1, 2)],
    # Tetròminós L (mida 4)
    [(0, 0), (0, 1), (0, 2), (1, 2)],
    [(0, 0), (1, 0), (2, 0), (2, 1)],
    [(0, 0), (1, 0), (1, 1), (1, 2)],
    [(0, 1), (1, 1), (2, 0), (2, 1)],
    # Tetròminós J (mida 4)
    [(0, 0), (0, 1), (0, 2), (1, 0)],
    [(0, 0), (1, 0), (2, 0), (0, 1)],
    [(0, 2), (1, 0), (1, 1), (1, 2)],
    [(0, 0), (0, 1), (1, 1), (2, 1)],
    # Tetròminós S (mida 4)
    [(0, 1), (1, 0), (1, 1), (2, 0)],
    [(0, 0), (0, 1), (1, 1), (1, 2)],
    # Tetròminós Z (mida 4)
    [(0, 0), (1, 0), (1, 1), (2, 1)],
    [(0, 1), (0, 2), (1, 0), (1, 1)],
]

# Formes de fallback de gran a petit per quan el taulell s'omple
_FALLBACKS = [
    [(0, 0), (0, 1)],
    [(0, 0), (1, 0)],
    [(0, 0)],
]


# ---------------------------------------------------------------------------
# Configuració dels nivells de dificultat
# ---------------------------------------------------------------------------

@dataclass
class NivellConfig:
    w_range:            tuple[int, int]
    h_range:            tuple[int, int]
    ocupacio:           float
    pesos_mida:         dict[int, int]
    amb_parets:         bool
    nombre_objectius:   int
    puntuacio_minima:   float
    max_intents:        int
    percentil_objectiu: int


NIVELLS: dict[str, NivellConfig] = {
    "easy": NivellConfig(
        w_range            = (4, 5),
        h_range            = (4, 5),
        ocupacio           = 0.55,
        pesos_mida         = {1: 5, 2: 4, 3: 2, 4: 1},
        amb_parets         = False,
        nombre_objectius   = 1,
        puntuacio_minima   = 0.8,
        max_intents        = 40,
        percentil_objectiu = 50,
    ),
    "medium": NivellConfig(
        w_range            = (5, 6),
        h_range            = (4, 5),
        ocupacio           = 0.70,
        pesos_mida         = {1: 1, 2: 5, 3: 6, 4: 3},
        amb_parets         = False,
        nombre_objectius   = 1,
        puntuacio_minima   = 1.5,
        max_intents        = 60,
        percentil_objectiu = 25,
    ),
    "hard": NivellConfig(
        w_range            = (5, 6),
        h_range            = (5, 7),
        ocupacio           = 0.72,
        pesos_mida         = {1: 3, 2: 4, 3: 5, 4: 3},
        amb_parets         = True,
        nombre_objectius   = 1,
        puntuacio_minima   = 3.5,
        max_intents        = 100,
        percentil_objectiu = 10,
    ),
}


# ---------------------------------------------------------------------------
# Funcions auxiliars
# ---------------------------------------------------------------------------

def _forma_ponderada(pesos_mida: dict[int, int]) -> list[tuple[int, int]]:
    formes_valides = [f for f in FORMES_CATALEG if pesos_mida.get(len(f), 0) > 0]
    pesos = [pesos_mida[len(f)] for f in formes_valides]
    return random.choices(formes_valides, weights=pesos, k=1)[0]


def _col_locar_peca(
    forma: list[tuple[int, int]],
    W: int,
    H: int,
    ocupades: set[tuple[int, int]],
) -> tuple[int, int] | None:
    max_dx = max(dx for dx, dy in forma)
    max_dy = max(dy for dx, dy in forma)
    candidats = [
        (px, py)
        for px in range(W - max_dx)
        for py in range(H - max_dy)
        if all((px + dx, py + dy) not in ocupades for dx, dy in forma)
    ]
    return random.choice(candidats) if candidats else None


def _generar_parets(W: int, H: int, n_walls: int) -> tuple[tuple[int, int], ...]:
    candidates = [
        (x, y) for x in range(W) for y in range(H)
        if not (x in (0, W - 1) and y in (0, H - 1))
    ]
    random.shuffle(candidates)
    return tuple(sorted(candidates[:n_walls]))


def _generar_objectius(
    peces: tuple[Piece, ...],
    posicions: tuple[tuple[int, int], ...],
    walls: tuple[tuple[int, int], ...],
    W: int,
    H: int,
    nombre_objectius: int,
    percentil: int,
) -> tuple[tuple[int, tuple[int, int]], ...]:
    walls_set = set(walls)
    idx_peces = sorted(range(len(peces)), key=lambda i: len(peces[i].coords), reverse=True)

    goals_list = []
    for p_idx in idx_peces[:nombre_objectius]:
        peça = peces[p_idx]
        pos_actual = posicions[p_idx]
        max_dx = max(dx for dx, dy in peça.coords)
        max_dy = max(dy for dx, dy in peça.coords)

        opcions = []
        for gx in range(W - max_dx):
            for gy in range(H - max_dy):
                if (gx, gy) == pos_actual:
                    continue
                if all((gx + dx, gy + dy) not in walls_set for dx, dy in peça.coords):
                    dist = abs(gx - pos_actual[0]) + abs(gy - pos_actual[1])
                    opcions.append((dist, (gx, gy)))

        if not opcions:
            continue

        opcions.sort(reverse=True)
        tall = max(1, len(opcions) * percentil // 100)
        _, (gx, gy) = random.choice(opcions[:tall])
        goals_list.append((p_idx, (gx, gy)))

    return tuple(sorted(goals_list))


# ---------------------------------------------------------------------------
# Generació principal del puzzle
# ---------------------------------------------------------------------------

def generar_puzzle(cfg: NivellConfig) -> Puzzle | None:
    W = random.randint(*cfg.w_range)
    H = random.randint(*cfg.h_range)

    walls: tuple[tuple[int, int], ...] = ()
    if cfg.amb_parets:
        n_walls = max(1, (W * H) // 12)
        walls = _generar_parets(W, H, n_walls)

    ocupades: set[tuple[int, int]] = set(walls)
    area_total = W * H - len(walls)
    caselles_lliures_min = 3 if cfg.amb_parets else 2
    area_max = int(area_total * cfg.ocupacio) - caselles_lliures_min

    if area_max <= 0:
        return None

    peces_generades: list[Piece] = []
    posicions_inicials: list[tuple[int, int]] = []
    area_actual = 0
    intents = 0

    while area_actual < area_max and intents < 400:
        intents += 1

        forma_coords = _forma_ponderada(cfg.pesos_mida)

        pos = None
        for candidata in [forma_coords] + _FALLBACKS:
            if area_actual + len(candidata) > area_max:
                continue
            pos = _col_locar_peca(candidata, W, H, ocupades)
            if pos is not None:
                forma_coords = candidata
                break

        if pos is None:
            break

        px, py = pos
        peça = Piece.normalized(forma_coords)
        peces_generades.append(peça)
        posicions_inicials.append((px, py))
        for dx, dy in forma_coords:
            ocupades.add((px + dx, py + dy))
        area_actual += len(forma_coords)

    if not peces_generades:
        return None

    pairs = sorted(zip(peces_generades, posicions_inicials))
    peces_final = tuple(p for p, _ in pairs)
    posicions_final = tuple(pos for _, pos in pairs)

    goals = _generar_objectius(
        peces_final, posicions_final, walls,
        W, H, cfg.nombre_objectius, cfg.percentil_objectiu,
    )
    if not goals:
        return None

    try:
        return Puzzle(
            W=W, H=H,
            walls=walls,
            pieces=peces_final,
            start=State(posicions_final),
            goals=goals,
        )
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Selecció del millor puzzle entre múltiples intents (Amb Telemetria Ràpida)
# ---------------------------------------------------------------------------

def generar_millor_puzzle(cfg: NivellConfig, nivell: str) -> tuple[Puzzle, dict]:
    millor_puzzle: Puzzle | None = None
    millor_resultat: dict = {"puntuacio": -1.0}

    for intent in range(1, cfg.max_intents + 1):
        print(f"  → Intent {intent:3d}/{cfg.max_intents}: Generant... ", end="", flush=True)
        
        pz = generar_puzzle(cfg)
        if pz is None:
            print("❌ Ignorat (No hi caben les peces)")
            continue

        if not possible_moves(pz, pz.start):
            print("❌ Ignorat (Taulell 100% bloquejat d'inici)")
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
        print(f"Error: no s'ha pogut generar cap puzzle '{nivell}' resoluble.")
        sys.exit(1)

    if millor_resultat["puntuacio"] < cfg.puntuacio_minima:
        print(f"\n  ⚠ No s'ha assolit la puntuació mínima ({cfg.puntuacio_minima}). "
              f"Es retorna el millor trobat ({millor_resultat['puntuacio']:.2f}).")

    return millor_puzzle, millor_resultat


# ---------------------------------------------------------------------------
# Punt d'entrada
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Ús: python3 {sys.argv[0]} <easy|medium|hard> <nom_puzzle>")
        sys.exit(1)

    nivell   = sys.argv[1].lower()
    nom_arxiu = sys.argv[2]

    if nivell not in NIVELLS:
        print(f"Error: nivell '{nivell}' desconegut. Usa 'easy', 'medium' o 'hard'.")
        sys.exit(1)

    cfg = NIVELLS[nivell]
    print(f"Generant puzzle '{nom_arxiu}' [nivell: {nivell.upper()}]...")
    print(f"  Taulell: {cfg.w_range[0]}-{cfg.w_range[1]}×{cfg.h_range[0]}-{cfg.h_range[1]}, "
          f"ocupació fins al {int(cfg.ocupacio*100)}%, "
          f"parets: {'sí' if cfg.amb_parets else 'no'}")

    millor, resultat = generar_millor_puzzle(cfg, nivell)

    path = Path(f"{nom_arxiu}.json")
    path.write_text(millor.to_json(indent=4))

    print(f"\nMillor puzzle guardat a '{path}'")
    imprimir_avaluacio(millor, resultat)