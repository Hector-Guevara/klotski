"""
Genera un nou puzzle en format .json en base a un nivell de dificultat, donat
per l'usuari entre 3 possibles opcions: easy, medium o hard.

També es poden afegir parets, dos objectius i les dues coses a la vegada o cap.

Característiques del generador:
- Taulells de 5x6 o 6x5 pel nivell "hard", menors en el cas "medium" i "easy".
- Densitat mil·limètrica (deixant entre 3 i 5 caselles lliures, pels nivells hard). Rebuig estricte si no s'assoleix.
- Parets estrictament CENTRALS per crear colls d'ampolla.
- Ús de formes complexes (L, T, Z) combinades amb peces petites.
- Generació Forward: Col·loca la peça més gran i l'envia a la cantonada oposada.
- Suporta els flags opcionals [wall] i [multigoal].

Ús: 
    python3 generate.py <easy/medium/hard> [wall] [multigoal] <nom_puzzle>
"""

from __future__ import annotations

import random
import sys
import os
from dataclasses import dataclass
from pathlib import Path

from puzzle import Puzzle, Piece, State
from eval import avaluar_puzzle, imprimir_avaluacio
from logic import possible_moves

# Catàleg de formes complet

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

# Peces més petites, en cas que el generador tingui problemes per tenir el taulell molt ple
_FALLBACKS = [[(0, 0), (0, 1)], [(0, 0), (1, 0)], [(0, 0)]]

# Configuració dels nivells de dificultat

@dataclass
class NivellConfig:
    """
    Estructura de dades que defineix els paràmetres de generació per a cada nivell de dificultat.
    """

    # Declaració d'atributs

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
        nombre_objectius=1, puntuacio_minima=1.0, max_intents=50,
    ),
    "medium": NivellConfig(
        dimensions=[(5, 5)], ocupacio=0.75,
        pesos_mida={1: 4, 2: 5, 3: 3, 4: 1}, amb_parets=False,
        nombre_objectius=1, puntuacio_minima=2.0, max_intents=100,
    ),
    "hard": NivellConfig(
        dimensions=[(5, 6), (6, 5)], 
        ocupacio=0.86, 
        pesos_mida={1: 3, 2: 6, 3: 4, 4: 3}, 
        amb_parets=False, 
        nombre_objectius=1, 
        puntuacio_minima=3.6, 
        max_intents=150, 
    ),
}

# Funcions auxiliars

def _forma_ponderada(pesos_mida: dict[int, int]) -> list[tuple[int, int]]:
    """
    Selecciona una forma aleatòria del catàleg ponderada pels pesos especificats.
    
    Pre: 'pesos_mida' és un diccionari vàlid que relaciona la mida de la peça amb el seu pes probabilístic.
    Post: Retorna una llista de coordenades corresponent a una forma triada a l'atzar segons els pesos.
    """
    formes_valides = [f for f in FORMES_CATALEG if pesos_mida.get(len(f), 0) > 0]
    pesos = [pesos_mida.get(len(f), 0) for f in formes_valides]
    return random.choices(formes_valides, weights=pesos, k=1)[0]

def _trobar_objectiu_lluny(
    peça: Piece, pos_actual: tuple[int, int], ocupades: set[tuple[int, int]], W: int, H: int
) -> tuple[int, int] | None:
    """
    Cerca una posició objectiu (meta) per a una peça que estigui el més lluny possible 
    de la seva posició inicial, sense solapar-se amb les caselles ja ocupades.
    
    Pre: 'peça' és un peça (Piece) vàlida, 'pos_actual' està dins del taulell WxH, i 
         'ocupades' és un conjunt de coordenades inaccessibles (ex: parets o altres metes).
    Post: Retorna la coordenada (x, y) de la meta ideal a una distància Manhattan >= 3. 
          Si no hi ha cap posició vàlida lliure, retorna None.
    """
    max_dx = max(dx for dx, _ in peça.coords)
    max_dy = max(dy for _, dy in peça.coords)

    opcions = []
    for gx in range(W - max_dx):
        for gy in range(H - max_dy):
            if (gx, gy) == pos_actual:
                continue
            if any((gx + dx, gy + dy) in ocupades for dx, dy in peça.coords):
                continue
                
            dist = abs(gx - pos_actual[0]) + abs(gy - pos_actual[1])
            # Forcem que la meta estigui a una distància mínima per evitar solucions trivials, i obtenir-ne millors puzzles
            if dist >= 3: 
                opcions.append((dist, (gx, gy)))

    if not opcions:
        return None

    opcions.sort(reverse=True)
    return opcions[0][1]

# Generació principal del puzzle (FORWARD GENERATION)

def generar_puzzle(cfg: NivellConfig, amb_parets: bool, multigoal: bool) -> Puzzle | None:
    """
    Genera un únic intent de puzzle aplicant l'estratègia de col·locació descrita.
    Introdueix parets i/o múltiples objectius dinàmicament si estan activats.
    
    Pre: 'cfg' és un NivellConfig vàlid. 'amb_parets' i 'multigoal' són booleans.
    Post: Retorna un objecte Puzzle vàlid si aconsegueix arribar a la densitat exigida 
          i assignar les metes correctament. Si el generador es bloqueja matemàticament 
          abans d'hora, retorna None.
    """
    W, H = random.choice(cfg.dimensions)

    walls_list: list[tuple[int, int]] = []
    if amb_parets:
        # Només 1 paret en nivells hard/densos per evitar bloquejos físics absoluts
        n_walls = 1 if cfg.ocupacio >= 0.85 else random.randint(1, 2)
        
        # Parets estrictament centrals per fer de coll d'ampolla
        candidats_parets = [(x, y) for x in range(2, W - 2) for y in range(2, H - 2)]
        if not candidats_parets: # Fallback per si W o H són massa petits
            candidats_parets = [(x, y) for x in range(1, W - 1) for y in range(1, H - 1)]
        
        if candidats_parets:
            random.shuffle(candidats_parets)
            walls_list = candidats_parets[:min(n_walls, len(candidats_parets))]

    walls = tuple(sorted(walls_list))
    ocupades: set[tuple[int, int]] = set(walls)
    
    area_total = W * H - len(walls)
    
    # Reducció de l'ocupació (oxigen), en cas que hi hagi parets
    marge_oxigen = 0.035 if cfg.ocupacio >= 0.85 else 0.05
    
    if amb_parets:
        # Es baixa l'ocupació un 6% addicional per l'aparició de parets en el puzzle
        marge_oxigen += 0.06 
    if amb_parets and multigoal:
        # S'afegeix un 3% més d'espai lliure (oxigen), si a més hi ha múltiples objectius
        marge_oxigen += 0.03
        
    ocupacio_real = cfg.ocupacio - marge_oxigen
    area_max = int(area_total * ocupacio_real)

    # Si hi ha parets, s'afegeixen més peces petites, per poder tenir més maniobra amb les peces grans
    # al voltant del mur en el puzzle
    pesos_usar = cfg.pesos_mida.copy()
    if amb_parets:
        if cfg.ocupacio >= 0.85: # En nivell Hard
            pesos_usar[1] += 4  # Més peces petites per maniobrar
            pesos_usar[4] = max(0, pesos_usar[4] - 2) # Reduïm dràsticament les gegants

    peces_generades: list[Piece] = []
    posicions_inicials: list[tuple[int, int]] = []
    area_actual = 0
    intents = 0

    formes_grans = [f for f in FORMES_CATALEG if len(f) == 4]
    forma_inicial = random.choice(formes_grans)
    
    while area_actual < area_max and intents < 200:
        intents += 1
        
        if area_actual == 0:
            forma_coords = forma_inicial
        else:
            forma_coords = _forma_ponderada(pesos_usar) # Usem els nous pesos
            
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

    # Si s'ha rendit sense omplir el taulell a la densitat exigida, descartem
    if area_actual < area_max - 1:
        return None

    if not peces_generades: return None

    # Ordenació canònica de sortida
    pairs = sorted(zip(peces_generades, posicions_inicials))
    peces_final = tuple(p for p, _ in pairs)
    posicions_final = tuple(pos for _, pos in pairs)

    nombre_objectius = 2 if multigoal else 1
    idx_peces = sorted(range(len(peces_final)), key=lambda i: len(peces_final[i].coords), reverse=True)
    
    goals_list = []
    # Creem un conjunt dinàmic que comença amb les parets
    ocupades_metes = set(walls)
    
    for i in range(min(nombre_objectius, len(idx_peces))):
        idx = idx_peces[i]
        pos_meta = _trobar_objectiu_lluny(peces_final[idx], posicions_final[idx], ocupades_metes, W, H)
        
        if pos_meta is not None:
            goals_list.append((idx, pos_meta))
            # Afegim les caselles d'aquesta meta a les 'ocupades'
            # perquè el següent objectiu no es col·loqui a sobre
            for dx, dy in peces_final[idx].coords:
                ocupades_metes.add((pos_meta[0] + dx, pos_meta[1] + dy))
        else:
            # Si un dels objectius no pot trobar lloc per culpa de parets o l'altre objectiu, descartem
            return None 

    if not goals_list or len(goals_list) < nombre_objectius:
        return None

    goals = tuple(sorted(goals_list))

    return Puzzle(
        W=W, H=H, walls=walls, pieces=peces_final, start=State(posicions_final), goals=goals
    )

# Cerca del millor puzzle

def generar_millor_puzzle(cfg: NivellConfig, nivell: str, amb_parets: bool, multigoal: bool) -> tuple[Puzzle, dict]:
    """
    Bucle de cerca iterativa que genera múltiples puzzles i avalua cadascun d'ells
    fins a assolir la nota objectiu del nivell. Aquesta puntuació és estipulada per cfg, el nivell
    de la classe
    
    Pre: 'cfg' conté el nombre màxim d'intents i la puntuació mínima desitjada.
    Post: Retorna una tupla (Puzzle, diccionari_resultats) amb el millor puzzle trobat. 
          Si no en troba cap de resoluble en tots els intents, atura el procés amb sys.exit(1).
    """
    millor_puzzle: Puzzle | None = None
    millor_resultat: dict = {"puntuacio": -1.0}

    for intent in range(1, cfg.max_intents + 1):
        print(f"  → Intent {intent:3d}/{cfg.max_intents}: Generant... ", end="", flush=True)
        
        pz = generar_puzzle(cfg, amb_parets, multigoal)
        if pz is None:
            print("❌ Ignorat (Massa forats lliures o metes invàlides)")
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

        print(f"✅ RESOLUBLE! ({resultat.get('num_estats', '?')} estats) — Nota: {resultat.get('puntuacio', 0):.2f}")

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
        print(f"Ús: python3 {sys.argv[0]} <easy|medium|hard> [wall] [multigoal] <nom_puzzle>")
        sys.exit(1)

    nivell = sys.argv[1].lower()
    nom_arxiu = sys.argv[-1]
    
    flags = [arg.lower() for arg in sys.argv[2:-1]]
    amb_parets = "wall" in flags
    multigoal = "multigoal" in flags
    
    if nivell not in NIVELLS:
        print(f"Error: nivell '{nivell}' desconegut. Usa 'easy', 'medium' o 'hard'.")
        sys.exit(1)
        
    cfg = NIVELLS[nivell]

    params_str = []
    if amb_parets: params_str.append("Parets")
    if multigoal: params_str.append("Multigoal")
    extres = f" [{'+'.join(params_str)}]" if params_str else ""

    print(f"Generant puzzle '{nom_arxiu}' [nivell: {nivell.upper()}]{extres}...")
    millor, resultat = generar_millor_puzzle(cfg, nivell, amb_parets, multigoal)

    # Desar el puzzle a la carpeta "puzzles"
    DEST_FOLDER = "puzzles"
    if not os.path.exists(DEST_FOLDER):
        os.makedirs(DEST_FOLDER)
        
    # Assegurar-nos que l'arxiu acabi en .json
    nom_base = nom_arxiu if nom_arxiu.endswith(".json") else f"{nom_arxiu}.json"
    path = Path(DEST_FOLDER) / nom_base
    path.write_text(millor.to_json(indent=4))

    print(f"\nMillor puzzle guardat a '{path}'")
    imprimir_avaluacio(millor, resultat)