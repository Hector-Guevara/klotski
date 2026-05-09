"""
Donats certs paràmetres, genera un nou puzzle en format .json tenint en compte les mesures d'interès establertes:
  - Longitud de la solució òptima (puzzles més llargs → més interessants)
  - Nombre total d'estats accessibles (espai de cerca gran → més complex)
  - Nombre d'estats finals (menys solucions → més difícil)
  - Proporció d'estats que formen part del camí òptim (eficiència del camí)
  - Centralitat de pont: si hi ha colls d'ampolla al graf (fases del puzzle)

Ús: python3 generate.py <nombre_peces> <amplada_taulell> <alçada_taulell> <parets/obstacles> <nombre_objectius> <nom_puzzle>,
on:
    nombre_peces: enter que dessigna el nombre de peces a generar per aquest puzzle (com a màxim, W·H-1 peces)
    amplada_taulell: enter que dessigna l'amplada del taulell (W)
    alçada_taulell: enter que dessigna l'alçada del taulell (H)
    parets/obstacles: string (si/no), que indica si es vol que hi hagi parets o no
    nombre_objectius: enter que dessigna el nombre d'objectius per aconseguir que el joc acabi
    nom_puzzle: string que dessigna el nom del puzzle a guardar (se li afegirà l'extensió .json automàticament)
"""

import json
import random
import sys

from pathlib import Path
from puzzle import Puzzle, Piece, State

from eval import avaluar_puzzle

def crear_peça_aleatoria() -> Piece:
    """Retorna una peça a l'atzar d'entre totes les possibles peces donades."""

    peces = {
        "1x1": [(0, 0)],
        "2x1": [(0, 0), (1, 0)],
        "1x2": [(0, 0), (0, 1)],
        "2x2": [(0, 0), (1, 0), (0, 1), (1, 1)],
        "L": [(0, 0), (0, 1), (0, 2), (1, 2)],
        "I": [(0, 0), (0, 1), (0, 2)],
        "T": [(0, 0), (1, 0), (2, 0), (1, 1)],
    }
    # se selecciona una peça
    peça = random.choice(list(peces.values()))

    return Piece.normalized(peça)

def generar_poliomino_aleatori(n_celdes: int) -> Piece:
    """
    Genera un poliomino aleatori de n caselles connectades.
    Utilitza l'algorisme de creixement per assegurar la contigüitat.
    """
    if n_celdes < 1:
        raise ValueError("El poliomino ha de tenir almenys una casella.")

    # Comencem amb una casella a l'origen
    coords = set([(0, 0)])
    
    # Conjunt de caselles candidates (les que toquen les que ja tenim)
    candidates = set([(0, 1), (0, -1), (1, 0), (-1, 0)])

    while len(coords) < n_celdes:
        # Triem una candidata a l'atzar i l'afegim a la peça
        nova_celda = random.choice(list(candidates))
        coords.add(nova_celda)
        candidates.remove(nova_celda)

        # Actualitzem els veïns de la nova celda que podrien ser candidats
        x, y = nova_celda
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            vei = (x + dx, y + dy)
            if vei not in coords:
                candidates.add(vei)

    # Usem el teu mètode static per normalitzar i ordenar la peça automàticament
    return Piece.normalized(list(coords))

def generar_puzzle(nombre_peces: int, W: int, H: int, parets: bool, nombre_objectius: int) -> Puzzle: 
    """Genera un nou puzzle tenint en compte els criteris d'interès."""
    
    # 1. Generar parets
    walls_list = []
    if parets:
        # Posem un nombre de parets proporcional a la mida (aprox 10%)
        n_walls = (W * H) // 10
        for _ in range(n_walls):
            wx, wy = random.randint(0, W-1), random.randint(0, H-1)
            walls_list.append((wx, wy))
    walls = tuple(sorted(set(walls_list)))

    # 2. Generar peces i posicions sense solapaments
    ocupades = set(walls)
    peces_generades = []
    posicions_inicials = []

    # mida màxima a ocupar, perquè pugui haver moviment de les peces
    MAX_AREA = (W * H) - 2
    area_actual = len(ocupades)

    intents_globals = 0
    while len(peces_generades) < nombre_peces and area_actual < MAX_AREA and intents_globals < 500:
        intents_globals += 1
        
        # Mida aleatòria de la peça (1 a 4 cel·les)
        mida = random.randint(1, 4)

        if area_actual + mida > MAX_AREA:
            mida = 1 # Intentamos poner una pieza pequeña si no cabe una grande

        forma = generar_poliomino_aleatori(mida)
        
        # Posició aleatòria
        px = random.randint(0, W - 1)
        py = random.randint(0, H - 1)
        
        # Validar si cap i no solapa
        celdes_abs = []
        possible = True
        for dx, dy in forma.coords:
            ax, ay = px + dx, py + dy
            if ax >= W or ay >= H or (ax, ay) in ocupades:
                possible = False
                break
            celdes_abs.append((ax, ay))
        
        if possible:
            peces_generades.append(forma)
            posicions_inicials.append((px, py))
            ocupades.update(celdes_abs)
            area_actual += len(forma.coords)

    # --- ORDRE CANÒNIC (Obligatori per a la classe Puzzle) ---
    # Ordenem per (Peça, Posició)
    pairs = sorted(zip(peces_generades, posicions_inicials))
    peces_final = tuple(p[0] for p in pairs)
    posicions_final = tuple(p[1] for p in pairs)

    celdas_libres_de_muros = []
    for x in range(W):
        for y in range(H):
            if (x, y) not in walls:
                celdas_libres_de_muros.append((x, y))

    # 3. Generar objectius aleatoris
    # Triem n peces a l'atzar per assignar-los un objectiu
    idx_peces = list(range(len(peces_final)))
    random.shuffle(idx_peces)

    goals_list = []

    for i in range(min(nombre_objectius, len(peces_final))):
        p_idx = idx_peces[i]
        peça = peces_final[p_idx]
        pos_actual = posicions_final[p_idx]
        
        # Buscamos posiciones (gx, gy) donde quepa TODA la pieza sin tocar muros
        opciones_validas = []
        
        for gx in range(W):
            for gy in range(H):
                if (gx, gy) == pos_actual:
                    continue
                
                toda_la_pieza_cabe = True
                for dx, dy in peça.coords:
                    ax, ay = gx + dx, gy + dy
                    # Comprobar límites y paredes
                    if ax >= W or ay >= H or (ax, ay) in walls:
                        toda_la_pieza_cabe = False
                        break
                
                if toda_la_pieza_cabe:
                    opciones_validas.append((gx, gy))
        
        if opciones_validas:
            gx, gy = random.choice(opciones_validas)
            goals_list.append((p_idx, (gx, gy)))

    goals = tuple(sorted(goals_list))

    return Puzzle(
        W=W, H=H,
        walls=walls,
        pieces=peces_final,
        start=State(posicions_final),
        goals=goals
    )


# FALTA IMPLEMENTAR EVALUACION (déjamelo a mí @jandroduets)

if __name__ == "__main__":
    if len(sys.argv) < 7:
        print(f"Ús: python3 {sys.argv[0]} <nombre_peces> <amplada_taulell> <alçada_taulell> <parets/obstacles> <nombre_objectius> <nom_puzzle>")
        sys.exit(1)

    # Parseig d'arguments
    n_peces = int(sys.argv[1])
    W = int(sys.argv[2])
    H = int(sys.argv[3])
    amb_parets = sys.argv[4].lower() == "si"
    n_objectius = int(sys.argv[5])
    nom_arxiu = sys.argv[6]

    # Generació
    print(f"Generant puzzle '{nom_arxiu}'...")
    nou_puzzle = generar_puzzle(n_peces, W, H, amb_parets, n_objectius)

    # Guardar a fitxer JSON
    path = Path(f"{nom_arxiu}.json")
    path.write_text(nou_puzzle.to_json(indent=4))
    
    print(f"Fet! Puzzle guardat a {path}")
    print(f"Peces generades: {len(nou_puzzle.pieces)}")