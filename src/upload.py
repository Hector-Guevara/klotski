"""
Llegeix un puzzle en format .json i l'envia al repositori compartit.
 
El flux és el següent:
  1. Llegeix i valida el puzzle des d'un fitxer .json local.
  2. Avalua el puzzle automàticament amb eval.py i en mostra les mètriques.
  3. Envia el puzzle al repositori via POST autenticat amb el token.
 
Ús:
    python3 upload.py <puzzle.json> <token>

    comanda en el shell de python per utilitzar-lo:

    python src/upload.py puzzles/mi_puzzle.json token
 
El servidor afegeix el puzzle a la llista. Si ja hi ha més de 200 puzzles,
substitueix a l'atzar un dels puzzles amb valoració més baixa.
"""
 
from __future__ import annotations
 
import sys
import json
import argparse
import urllib.request
import urllib.error
from pathlib import Path
 
from puzzle import Puzzle
from eval import avaluar_puzzle, imprimir_avaluacio
 
# ---------------------------------------------------------------------------
# Configuració del repositori (mateixa base que download.py i rate.py)
# ---------------------------------------------------------------------------
 
BASE_URL = "https://klotski.pauek.dev/api/puzzles"
 
 
 
# ---------------------------------------------------------------------------
# Funcions de comunicació amb el repositori
# ---------------------------------------------------------------------------
 
def enviar_puzzle(pz: Puzzle, token: str) -> str:
    """
    Envia un puzzle nou al repositori via POST autenticat amb el token Bearer.
    Retorna l'ID assignat pel servidor al puzzle enviat.
    """
    # es serialitza el puzzle al format JSON estàndard de la pràctica.
    # El servidor espera el puzzle directe a l'arrel ({"W":...,"H":...}),
    # no embolcallat. L'embolcall {"puzzle":..., "stars":...} és només
    # el format de la resposta GET, no del POST.
    cos = pz.to_json().encode()
 
    # es construeix la petició POST amb el token a la capçalera d'autenticació
    peticio = urllib.request.Request(
        BASE_URL,
        data=cos,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
 
    try:
        with urllib.request.urlopen(peticio) as response:
            resposta_raw = response.read().decode()
 
        # el servidor retorna l'ID del puzzle creat; pot venir com a JSON o com a string pla
        try:
            resposta = json.loads(resposta_raw)
            # si la resposta és un dict amb un camp 'id', l'extraiem
            puzzle_id = resposta.get("id", resposta_raw) if isinstance(resposta, dict) else str(resposta)
        except json.JSONDecodeError:
            # si no és JSON vàlid, tractem la resposta com a ID directament
            puzzle_id = resposta_raw.strip()
 
        return puzzle_id
 
    except urllib.error.HTTPError as e:
        # es llegeix el cos de l'error per mostrar el missatge del servidor
        detall = e.read().decode() if e.fp else ""
        print(f"Error HTTP {e.code} en enviar el puzzle: {e.reason}")
        if detall:
            print(f"Detall: {detall}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error de connexió: {e.reason}")
        sys.exit(1)
 
 
# ---------------------------------------------------------------------------
# Flux principal
# ---------------------------------------------------------------------------
 
def pujar_puzzle(puzzle_path: Path, token: str) -> None:
    """
    Orquestra el flux complet: llegeix, avalua i envia el puzzle al repositori.
    """
 
    # pas 1: lectura i validació del fitxer local
    # Puzzle.from_json ja llença ValueError si el format és incorrecte
    print(f"Llegint puzzle des de '{puzzle_path}'...")
    try:
        pz = Puzzle.from_json(puzzle_path.read_text())
    except (ValueError, KeyError) as e:
        print(f"Error en llegir el puzzle: {e}")
        sys.exit(1)
 
    print(f"Puzzle vàlid: {pz.W}×{pz.H}, {len(pz.pieces)} peces, {len(pz.goals)} objectiu(s)")
 
    # pas 2: avaluació automàtica per informar l'usuari de la qualitat del puzzle
    print("\nAvaluant el puzzle abans d'enviar...")
    resultat = avaluar_puzzle(pz)
    imprimir_avaluacio(pz, resultat)
 
    # avisem si la puntuació és molt baixa, però no bloquejem l'enviament
    if resultat["puntuacio"] < 1.0:
        print("\n⚠️  Advertència: la puntuació és baixa (< 1.0). El puzzle pot ser poc interessant.")
        print("   Continuant l'enviament igualment...")
 
    # pas 3: enviament al repositori
    print(f"\nEnviant puzzle al repositori ({BASE_URL})...")
    puzzle_id = enviar_puzzle(pz, token)
 
    print(f"\n✓ Puzzle enviat correctament!")
    print(f"  ID assignat: {puzzle_id}")
    print(f"  Puntuació:   {resultat['puntuacio']:.2f} / 5.00")
 
 
# ---------------------------------------------------------------------------
# Punt d'entrada
# ---------------------------------------------------------------------------
 
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Envia un puzzle .json al repositori compartit de Klotski."
    )
    parser.add_argument(
        "puzzle",
        type=Path,
        help="Fitxer .json del puzzle a enviar",
    )
    parser.add_argument(
        "token",
        help="Token d'autenticació Bearer per enviar puzzles",
    )
 
    args = parser.parse_args()
 
    # comprovem que el fitxer existeix abans de fer res
    if not args.puzzle.exists():
        print(f"Error: no s'ha trobat el fitxer '{args.puzzle}'")
        sys.exit(1)
 
    pujar_puzzle(args.puzzle, args.token)
 