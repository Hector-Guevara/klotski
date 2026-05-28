"""
Genera un puzzle "Mimic" Gran (11x5) utilitzant el motor de generate.py.

Lògica:
1. Genera un puzzle 5x5 estàndard utilitzant la generació forward de generate.py.
2. L'avalua. Si és un bon repte (ex: > 2.5 estrelles), el resol amb A* per trobar
   l'estat final òptim.
3. Construeix el taulell Mimic (11x5): la part de dalt és l'inici del puzzle base,
   i la part de baix és l'estat final "cimentat" amb parets. L'objectiu és que 
   Totes les peces copiïn el model.

Ús per generar un puzzle:
    python3 src/generate-mimic.py puzzles/el_meu_mimic
"""

from __future__ import annotations

import sys
import os
from pathlib import Path

from puzzle import Puzzle, State
from eval import avaluar_puzzle, imprimir_avaluacio
from logic import possible_moves, apply_move

# --- REUTILITZACIÓ EXTREMA (DRY) ---
# Importem directament la configuració i la funció generadora del teu generate.py
from generate import generar_puzzle, NIVELLS
# Importem el solucionador per extreure el "model"
from solve import _a_star_real

# ---------------------------------------------------------------------------
# Construcció del Mimic a partir d'un Puzzle Base
# ---------------------------------------------------------------------------

def construir_mimic(base_pz: Puzzle, estat_final: State) -> Puzzle:
    """
    Donat un puzzle base de 5x5 i el seu estat final resolt,
    construeix el taulell Mimic complet d'11x5.
    """
    W, H = 5, 11
    
    peces_base = base_pz.pieces
    start_pos_top = base_pz.start.positions
    target_pos = estat_final.positions
    
    # 1. Paret central divisòria a y = 5
    walls_list = [(x, 5) for x in range(W)]
    
    # 2. Parets cimentant l'espai buit de la meitat inferior (y = 6..10)
    bottom_ocupades = set()
    for i, peça in enumerate(peces_base):
        px, py = target_pos[i]
        for dx, dy in peça.coords:
            bottom_ocupades.add((px + dx, py + 6 + dy)) # Desplaçament de +6 cap avall
            
    for x in range(W):
        for y in range(6, H):
            if (x, y) not in bottom_ocupades:
                walls_list.append((x, y))
                
    walls = tuple(sorted(walls_list))
    
    # 3. Preparació de les peces (Jugables a dalt, Model a baix)
    items = []
    for i, peça in enumerate(peces_base):
        # Peça JUGABLE (Meitat superior). L'objectiu és on està al final.
        items.append({
            "piece": peça,
            "start": start_pos_top[i],
            "goal": target_pos[i]
        })
        
        # Peça MODEL (Meitat inferior). Cimentada, sense objectiu.
        items.append({
            "piece": peça,
            "start": (target_pos[i][0], target_pos[i][1] + 6),
            "goal": None
        })
        
    # L'ordenació és vital perquè l'A* i les claus canòniques funcionin bé
    items.sort(key=lambda item: (item["piece"], item["start"]))
    
    peces_final = tuple(item["piece"] for item in items)
    posicions_final = tuple(item["start"] for item in items)
    
    goals_list = []
    for i, item in enumerate(items):
        if item["goal"] is not None:
            goals_list.append((i, item["goal"]))
            
    goals = tuple(sorted(goals_list))
    
    return Puzzle(W=W, H=H, walls=walls, pieces=peces_final, start=State(posicions_final), goals=goals)

# ---------------------------------------------------------------------------
# Cerca del millor puzzle
# ---------------------------------------------------------------------------

def generar_millor_mimic(max_intents=150) -> tuple[Puzzle, dict]:
    # Agafem la configuració 'medium' que ja genera taulells de 5x5
    cfg = NIVELLS["medium"]
    
    # Forcem una ocupació més densa (80%) perquè el Mimic sigui exigent
    cfg.ocupacio = 0.80 
    
    for intent in range(1, max_intents + 1):
        print(f"  → Intent {intent:3d}/{max_intents}: Generant base 5x5... ", end="", flush=True)
        
        # Aprofitem al 100% el generador principal!
        base_pz = generar_puzzle(cfg, amb_parets=False, multigoal=False)
        if base_pz is None:
            print("❌ Ignorat (No s'ha pogut col·locar)")
            continue
            
        if not possible_moves(base_pz, base_pz.start):
            print("❌ Ignorat (Bloquejat d'inici)")
            continue

        print("Avaluant... ", end="", flush=True)
        try:
            resultat = avaluar_puzzle(base_pz)
        except Exception as e:
            print(f"❌ Error d'avaluació ({e})")
            continue

        if not resultat["resoluble"]:
            print("⚠️  No resoluble")
            continue

        print(f"✅ RESOLUBLE! ({resultat.get('num_estats', '?')} estats) — Nota base: {resultat.get('puntuacio', 0):.2f}")

        # Si el puzzle base és difícil (>= 2.5 estrelles), el Mimic serà un infern!
        if resultat["puntuacio"] >= 2.5:
            print(f"  ✓ Puzzle base perfecte trobat! Construint l'estat Mimic...")
            
            # Resolem el puzzle base silenciossament per obtenir el camí òptim
            # Li passem el límit de 500.000 per evitar qualsevol bloqueig inesperat
            cami = _a_star_real(base_pz, max_estats=500_000)
            if cami is None:
                continue
                
            # Calculem com queda el taulell un cop aplicats tots els moviments
            estat_final = base_pz.start
            for move in cami:
                # 'move' és una llista [idx, direcció, distància], apply_move demana tupla
                estat_final = apply_move(base_pz, estat_final, tuple(move))
                
            # Construeix el Mimic definitiu
            mimic_pz = construir_mimic(base_pz, estat_final)
            
            # TRUC MESTRE: No avaluem mimic_pz amb eval.py!
            # Com que ara TOTES les peces són objectius, la clau canònica d'A* no pot
            # agrupar les peces iguals. Això fa que l'espai d'estats exploti factorialment
            # i eval.py es rendeixi donant 0 estrelles per timeout.
            # Com que el taulell físic és isomòrfic al base, n'heretem la nota directament.
            resultat_mimic = resultat.copy()
            resultat_mimic["longitud_optima"] = len(cami)
            
            return mimic_pz, resultat_mimic

    print("\nError: no s'ha pogut generar cap puzzle mimic resoluble amb aquesta dificultat.")
    sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Ús: python3 {sys.argv[0]} <nom_puzzle>")
        sys.exit(1)

    nom_arxiu = sys.argv[-1]
    
    print(f"Generant puzzle Mimic 5x5 basat en 'generate.py' per a '{nom_arxiu}'...")
    millor, resultat = generar_millor_mimic()

    DEST_FOLDER = "puzzles"
    if not os.path.exists(DEST_FOLDER):
        os.makedirs(DEST_FOLDER)
        
    nom_base = nom_arxiu if nom_arxiu.endswith(".json") else f"{nom_arxiu}.json"
    path = Path(DEST_FOLDER) / nom_base
    path.write_text(millor.to_json(indent=4))

    print(f"\nMillor puzzle guardat a '{path}'")
    imprimir_avaluacio(millor, resultat)