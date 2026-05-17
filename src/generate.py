"""
Donats certs paràmetres, genera un nou puzzle en format .json tenint en compte les mesures d'interès establertes:
  - Longitud de la solució òptima (puzzles més llargs → més interessants)
  - Nombre total d'estats accessibles (espai de cerca gran → més complex)
  - Nombre d'estats finals (menys solucions → més difícil)
  - Proporció d'estats que formen part del camí òptim (eficiència del camí)
  - Centralitat de pont: si hi ha colls d'ampolla al graf (fases del puzzle)

Ús: python3 generate.py <nombre_peces> <amplada_taulell> <alçada_taulell> <parets/obstacles> <nombre_objectius> <nom_puzzle>
on:
    nombre_peces:     enter que designa el nombre de peces a generar (màxim W·H-2)
    amplada_taulell:  enter que designa l'amplada del taulell (W)
    alçada_taulell:   enter que designa l'alçada del taulell (H)
    parets/obstacles: string (si/no), indica si es vol que hi hagi parets
    nombre_objectius: enter que designa el nombre d'objectius
    nom_puzzle:       string amb el nom del fitxer (s'afegeix .json automàticament)
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

from puzzle import Puzzle, Piece, State
from eval import avaluar_puzzle, imprimir_avaluacio

# ---------------------------------------------------------------------------
# Paràmetres de generació
# ---------------------------------------------------------------------------

MAX_INTENTS    = 100   # intents màxims per trobar un puzzle prou bo
PUNTUACIO_MINIMA = 1  # puntuació mínima acceptable

# Pesos per mida de peça: afavorim mida 2-3, reduïm mida 4 (difícil de col·locar)
PESOS_MIDA = {1: 1, 2: 5, 3: 6, 4: 3}

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

# Formes de fallback ordenades de gran a petit per quan el taulell s'omple
_FALLBACKS = [
    [(0, 0), (0, 1)],  # dòmino vertical
    [(0, 0), (1, 0)],  # dòmino horitzontal
    [(0, 0)],          # monominó
]


# ---------------------------------------------------------------------------
# Funcions auxiliars
# ---------------------------------------------------------------------------

def _forma_aleatoria_ponderada() -> list[tuple[int, int]]:
    """Tria una forma del catàleg ponderada per mida."""
    pesos = [PESOS_MIDA[len(f)] for f in FORMES_CATALEG]
    return random.choices(FORMES_CATALEG, weights=pesos, k=1)[0]


def _col_locar_peca(
    forma: list[tuple[int, int]],
    W: int,
    H: int,
    ocupades: set[tuple[int, int]],
) -> tuple[int, int] | None:
    """
    Retorna una posició vàlida aleatòria per col·locar la peça, o None si no hi cap.
    max_dx és l'offset x màxim de la forma (0-indexat), per tant la darrera
    posició vàlida de px és W-1-max_dx, i range(W - max_dx) és correcte.
    """
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
    """Genera parets evitant les quatre cantonades per no bloquejar el taulell."""
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
) -> tuple[tuple[int, tuple[int, int]], ...]:
    """
    Genera objectius maximitzant la dificultat:
      - Prioritza les peces més grans (menys nodes goal → unicitat alta).
      - Escull la posició destí del 20% més llunyà en distància Manhattan
        (millor correlació amb longitud de solució que el terç anterior).
    """
    walls_set = set(walls)
    # peces més grans primer: menys posicions goal → puntuació unicitat més alta
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
        tall = max(1, len(opcions) // 5)  # 20% més llunyà
        _, (gx, gy) = random.choice(opcions[:tall])
        goals_list.append((p_idx, (gx, gy)))

    return tuple(sorted(goals_list))


# ---------------------------------------------------------------------------
# Generació principal del puzzle
# ---------------------------------------------------------------------------

def generar_puzzle(
    nombre_peces: int, W: int, H: int, parets: bool, nombre_objectius: int
) -> Puzzle | None:
    """
    Genera un puzzle aleatori col·locant peces fins a nombre_peces o fins que
    el taulell estigui ple (deixant sempre 2 caselles lliures per permetre moviment).
    Si una peça gran no hi cap, prova amb peces progressivament més petites
    per evitar que el generador es quedi encallat.
    """
    # 1. Parets
    walls: tuple[tuple[int, int], ...] = ()
    if parets:
        n_walls = max(1, (W * H) // 10)
        walls = _generar_parets(W, H, n_walls)

    ocupades: set[tuple[int, int]] = set(walls)
    area_max = W * H - len(walls) - 2  # mínim 2 caselles lliures

    peces_generades: list[Piece] = []
    posicions_inicials: list[tuple[int, int]] = []
    area_actual = 0
    intents = 0

    while len(peces_generades) < nombre_peces and intents < 300:
        intents += 1

        forma_coords = _forma_aleatoria_ponderada()

        # si la forma triada no hi cap, provem fallbacks progressivament més petits
        pos = None
        for candidata in [forma_coords] + _FALLBACKS:
            if area_actual + len(candidata) > area_max:
                continue
            pos = _col_locar_peca(candidata, W, H, ocupades)
            if pos is not None:
                forma_coords = candidata
                break

        if pos is None:
            break  # taulell ple, no hi cap cap peça més

        px, py = pos
        peça = Piece.normalized(forma_coords)
        peces_generades.append(peça)
        posicions_inicials.append((px, py))
        for dx, dy in forma_coords:
            ocupades.add((px + dx, py + dy))
        area_actual += len(forma_coords)

    if not peces_generades:
        return None

    # 2. Ordre canònic obligatori per a la classe Puzzle
    pairs = sorted(zip(peces_generades, posicions_inicials))
    peces_final = tuple(p for p, _ in pairs)
    posicions_final = tuple(pos for _, pos in pairs)

    # 3. Objectius
    goals = _generar_objectius(
        peces_final, posicions_final, walls, W, H, nombre_objectius
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
# Selecció del millor puzzle entre múltiples intents
# ---------------------------------------------------------------------------

def generar_millor_puzzle(
    nombre_peces: int, W: int, H: int, parets: bool, nombre_objectius: int
) -> tuple[Puzzle, dict]:
    """
    Genera fins a MAX_INTENTS puzzles i retorna el millor segons eval.py.
    Descarta explícitament puzzles irresolubles.
    """
    millor_puzzle: Puzzle | None = None
    millor_resultat: dict = {"puntuacio": -1.0}

    for intent in range(1, MAX_INTENTS + 1):
        pz = generar_puzzle(nombre_peces, W, H, parets, nombre_objectius)
        if pz is None:
            continue

        try:
            resultat = avaluar_puzzle(pz)
        except Exception:
            continue

        if not resultat["resoluble"]:
            continue

        print(f"  Intent {intent:2d}/{MAX_INTENTS}: puntuació {resultat['puntuacio']:.2f} / 5.00")

        if resultat["puntuacio"] > millor_resultat["puntuacio"]:
            millor_puzzle = pz
            millor_resultat = resultat

        if millor_resultat["puntuacio"] >= PUNTUACIO_MINIMA:
            print(f"  ✓ Puntuació acceptable trobada a l'intent {intent}.")
            break

    if millor_puzzle is None:
        print("Error: no s'ha pogut generar cap puzzle vàlid.")
        sys.exit(1)

    return millor_puzzle, millor_resultat


# ---------------------------------------------------------------------------
# Punt d'entrada
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 7:
        print(
            f"Ús: python3 {sys.argv[0]} "
            "<nombre_peces> <amplada_taulell> <alçada_taulell> "
            "<parets/obstacles> <nombre_objectius> <nom_puzzle>"
        )
        sys.exit(1)

    n_peces     = int(sys.argv[1])
    W           = int(sys.argv[2])
    H           = int(sys.argv[3])
    amb_parets  = sys.argv[4].lower() == "si"
    n_objectius = int(sys.argv[5])
    nom_arxiu   = sys.argv[6]

    print(f"Generant puzzle '{nom_arxiu}' ({W}×{H}, {n_peces} peces)...")
    millor, resultat = generar_millor_puzzle(n_peces, W, H, amb_parets, n_objectius)

    path = Path(f"{nom_arxiu}.json")
    path.write_text(millor.to_json(indent=4))

    print(f"\nMillor puzzle guardat a '{path}'")
    imprimir_avaluacio(millor, resultat)