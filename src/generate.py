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

import json
import random
import sys
from pathlib import Path

from puzzle import Puzzle, Piece, State
from eval import avaluar_puzzle, imprimir_avaluacio

# ---------------------------------------------------------------------------
# Paràmetres de generació
# ---------------------------------------------------------------------------

# Nombre màxim d'intents per trobar un puzzle prou bo, he decidido poner 60, aun que con 40 probablemente serian suficientes para asegurarme de encontrar un caso ideal, 80 tambien seria una posibilidad a estudiar
MAX_INTENTS = 60

# Puntuació mínima acceptable per guardar el puzzle
PUNTUACIO_MINIMA = 1.5

# Fracció d'ocupació del taulell: puzzles densos → grafs més grans → millor puntuació
# Un taulell gairebé ple (poques caselles lliures) genera molt més espai d'estats
OCUPACIO_OBJECTIU = 0.70

# Distància mínima de Manhattan entre posició inicial i objectiu d'una peça
# Objectius llunyans → solucions més llargues → millor puntuació
DISTANCIA_MIN_OBJECTIU = 3


# ---------------------------------------------------------------------------
# Catàleg de formes: evitem excés de peces 1x1 (que simplifiquen el graf)
# Les peces més grans restringeixen més els moviments → grafs més interessants
# ---------------------------------------------------------------------------

# Totes les orientacions possibles de cada família de poliominós fins a mida 4
FORMES_CATALEG: list[list[tuple[int, int]]] = [
    # Dòminos (mida 2) — 2 orientacions
    [(0, 0), (1, 0)],
    [(0, 0), (0, 1)],
    # Triòminós I (mida 3) — 2 orientacions
    [(0, 0), (1, 0), (2, 0)],
    [(0, 0), (0, 1), (0, 2)],
    # Triòminós L (mida 3) — 4 orientacions
    [(0, 0), (0, 1), (1, 0)],
    [(0, 0), (1, 0), (1, 1)],
    [(0, 1), (1, 0), (1, 1)],
    [(0, 0), (0, 1), (1, 1)],
    # Tetròminós O (mida 4) — 1 orientació
    [(0, 0), (0, 1), (1, 0), (1, 1)],
    # Tetròminós I (mida 4) — 2 orientacions
    [(0, 0), (1, 0), (2, 0), (3, 0)],
    [(0, 0), (0, 1), (0, 2), (0, 3)],
    # Tetròminós T (mida 4) — 4 orientacions
    [(0, 0), (1, 0), (2, 0), (1, 1)],
    [(0, 0), (0, 1), (0, 2), (1, 1)],
    [(0, 1), (1, 0), (1, 1), (2, 1)],
    [(0, 1), (1, 0), (1, 1), (1, 2)],
    # Tetròminós L (mida 4) — 4 orientacions
    [(0, 0), (0, 1), (0, 2), (1, 2)],
    [(0, 0), (1, 0), (2, 0), (2, 1)],  # corregit
    [(0, 0), (1, 0), (1, 1), (1, 2)],
    [(0, 1), (1, 1), (2, 0), (2, 1)],
    # Tetròminós J (mida 4) — 4 orientacions
    [(0, 0), (0, 1), (0, 2), (1, 0)],
    [(0, 0), (1, 0), (2, 0), (0, 1)],  # corregit
    [(0, 2), (1, 0), (1, 1), (1, 2)],
    [(0, 0), (0, 1), (1, 1), (2, 1)],
    # Tetròminós S (mida 4) — 2 orientacions
    [(0, 1), (1, 0), (1, 1), (2, 0)],
    [(0, 0), (0, 1), (1, 1), (1, 2)],
    # Tetròminós Z (mida 4) — 2 orientacions
    [(0, 0), (1, 0), (1, 1), (2, 1)],
    [(0, 1), (0, 2), (1, 0), (1, 1)],
]

# Pesos de mostreig: afavorim peces de mida 2-4 per sobre de les 1x1
# (les peces grans restringeixen més el taulell i fan puzzles més complexos)
PESOS_MIDA = {1: 1, 2: 4, 3: 6, 4: 5}


# ---------------------------------------------------------------------------
# Generació de peces
# ---------------------------------------------------------------------------

def _forma_aleatoria_ponderada() -> list[tuple[int, int]]:
    """
    Tria una forma del catàleg ponderada per mida.
    Afavoreix peces de mida 2-4 per generar puzzles més densos i complexos.
    """
    # construïm la llista de pesos per a cada forma del catàleg
    pesos = [PESOS_MIDA[len(f)] for f in FORMES_CATALEG]
    forma = random.choices(FORMES_CATALEG, weights=pesos, k=1)[0]
    return forma


def _col·locar_peca(
    forma: list[tuple[int, int]],
    W: int,
    H: int,
    ocupades: set[tuple[int, int]],
) -> tuple[int, int] | None:
    """
    Intenta col·locar una peça al taulell en una posició vàlida aleatòria.
    Retorna la posició (px, py) si és possible, o None si no hi cap.
    Fa múltiples intents aleatoris abans de rendir-se.
    """
    # calculem el desplaçament màxim vàlid per a aquesta forma
    max_dx = max(dx for dx, dy in forma)
    max_dy = max(dy for dx, dy in forma)

    # llista de totes les posicions vàlides on podria cabre la peça
    candidats = [
        (px, py)
        for px in range(W - max_dx)
        for py in range(H - max_dy)
        if all((px + dx, py + dy) not in ocupades for dx, dy in forma)
    ]

    if not candidats:
        return None

    return random.choice(candidats)


# ---------------------------------------------------------------------------
# Generació de parets
# ---------------------------------------------------------------------------

def _generar_parets(W: int, H: int, n_walls: int) -> tuple[tuple[int, int], ...]:
    """
    Genera parets en posicions que no bloquegin completament el taulell.
    Evita les cantonades i els centres per no crear zones inaccessibles.
    """
    candidates = [
        (x, y) for x in range(W) for y in range(H)
        # evitem les cantonades extremes que tendeixen a bloquejar massa
        if not (x in (0, W - 1) and y in (0, H - 1))
    ]
    random.shuffle(candidates)
    return tuple(sorted(candidates[:n_walls]))


# ---------------------------------------------------------------------------
# Generació d'objectius
# ---------------------------------------------------------------------------

def _distancia_manhattan(pos1: tuple[int, int], pos2: tuple[int, int]) -> int:
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])


def _generar_objectius(
    peces: tuple[Piece, ...],
    posicions: tuple[tuple[int, int], ...],
    walls: tuple[tuple[int, int], ...],
    W: int,
    H: int,
    nombre_objectius: int,
) -> tuple[tuple[int, tuple[int, int]], ...]:
    """
    Genera objectius que estiguin lluny de la posició inicial de la peça.
    Objectius llunyans → solucions més llargues → millor puntuació a eval.py.
    """
    walls_set = set(walls)
    idx_peces = list(range(len(peces)))
    random.shuffle(idx_peces)

    goals_list = []

    for p_idx in idx_peces[:nombre_objectius]:
        peça = peces[p_idx]
        pos_actual = posicions[p_idx]
        max_dx = max(dx for dx, dy in peça.coords)
        max_dy = max(dy for dx, dy in peça.coords)

        # recollim totes les posicions vàlides on cap la peça, ordenades per distància decreixent
        opcions = []
        for gx in range(W - max_dx):
            for gy in range(H - max_dy):
                if (gx, gy) == pos_actual:
                    continue
                # la peça ha de cabre sencera sense tocar parets
                if all(
                    (gx + dx, gy + dy) not in walls_set
                    for dx, dy in peça.coords
                ):
                    dist = _distancia_manhattan(pos_actual, (gx, gy))
                    opcions.append((dist, (gx, gy)))

        if not opcions:
            continue

        # ordenem per distància decreixent i agafem del terç superior (les més llunyanes)
        opcions.sort(reverse=True)
        tall = max(1, len(opcions) // 3)
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
    Genera un puzzle aleatori intentant maximitzar la complexitat:
      - Taulell dens (prop de OCUPACIO_OBJECTIU d'ocupació)
      - Peces de mida 2-4 preferentment (restringeixen més el moviment)
      - Objectius llunyans de la posició inicial (solucions més llargues)
    Retorna None si no s'ha pogut generar un puzzle vàlid.
    """

    # 1. Parets
    walls: tuple[tuple[int, int], ...] = ()
    if parets:
        n_walls = max(1, (W * H) // 10)
        walls = _generar_parets(W, H, n_walls)

    ocupades: set[tuple[int, int]] = set(walls)


    peces_generades: list[Piece] = []
    posicions_inicials: list[tuple[int, int]] = []
    area_actual = 0

    intents = 0

    while len(peces_generades) < nombre_peces and intents < 300: #no cal area max ja que el col·locar peça ja gestiona l'espai lliure

        intents += 1

        forma_coords = _forma_aleatoria_ponderada()
        mida = len(forma_coords)


        
        pos = _col·locar_peca(forma_coords, W, H, ocupades)
        if pos is None:
            # si no cabe, provar amb domino o monomino
            for fallback in [[(0,0),(0,1)], [(0,0),(1,0)], [(0,0)]]:
                pos = _col·locar_peca(fallback, W, H, ocupades)
                if pos is not None:
                    forma_coords = fallback
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

    # 3. Ordre canònic obligatori per a la classe Puzzle
    pairs = sorted(zip(peces_generades, posicions_inicials))
    peces_final = tuple(p for p, _ in pairs)
    posicions_final = tuple(pos for _, pos in pairs)

    # 4. Objectius llunyans
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
    Genera fins a MAX_INTENTS puzzles i en retorna el millor segons eval.py.
    Substitueix la recursió il·limitada de la versió anterior per un bucle
    amb límit fix, cosa que evita desbordaments de pila i temps d'execució
    imprevisibles.
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
            # grafs buits o puzzles trivials poden fallar a eval
            continue

        if not resultat["resoluble"]:
            continue

        print(f"  Intent {intent:2d}/{MAX_INTENTS}: puntuació {resultat['puntuacio']:.2f} / 5.00")

        if resultat["puntuacio"] > millor_resultat["puntuacio"]:
            millor_puzzle = pz
            millor_resultat = resultat

        # si ja tenim un puzzle prou bo, parem abans d'exhaurir els intents
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

    n_peces      = int(sys.argv[1])
    W            = int(sys.argv[2])
    H            = int(sys.argv[3])
    amb_parets   = sys.argv[4].lower() == "si"
    n_objectius  = int(sys.argv[5])
    nom_arxiu    = sys.argv[6]

    print(f"Generant puzzle '{nom_arxiu}' ({W}×{H}, {n_peces} peces)...")
    millor, resultat = generar_millor_puzzle(n_peces, W, H, amb_parets, n_objectius)

    path = Path(f"{nom_arxiu}.json")
    path.write_text(millor.to_json(indent=4))

    print(f"\nMillor puzzle guardat a '{path}'")
    imprimir_avaluacio(millor, resultat)