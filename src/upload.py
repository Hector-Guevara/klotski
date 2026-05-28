"""
Llegeix un puzzle en format .json i l'envia al repositori compartit.
 
El flux és el següent:
  1. Llegeix i valida el puzzle des d'un fitxer .json local.
  2. Avalua el puzzle automàticament amb eval.py i en mostra les mètriques.
  3. Envia el puzzle al repositori via POST autenticat amb el token.
 
Ús:
    python3 upload.py <puzzle.json> <token>
 
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
from download import BASE_URL

# Funcions de comunicació amb el repositori
 
def enviar_puzzle(pz: Puzzle, token: str) -> str:
    """
    Envia un puzzle instanciat al repositori via petició POST autenticada.
    
    Pre: 'pz' és un objecte Puzzle vàlid preparat per a ser serialitzat. 
         'token' és una cadena de text d'autenticació (Bearer) vàlida.
    Post: Retorna l'ID assignat pel servidor al puzzle (string). Si la connexió falla, 
          el token és invàlid (HTTP 401) o hi ha errors de servidor, s'informa 
          l'usuari per pantalla i s'atura l'execució (sys.exit(1)).
    """
    # Es serialitza el puzzle al format JSON estàndard de la pràctica.

    cos = pz.to_json().encode()
 
    # Es construeix la petició POST amb el token a la capçalera d'autenticació
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
 
        # El servidor retorna l'ID del puzzle creat; pot venir com a JSON o com a string pla
        try:
            resposta = json.loads(resposta_raw)
            # Si la resposta és un dict amb un camp 'id', l'extraiem
            puzzle_id = resposta.get("id", resposta_raw) if isinstance(resposta, dict) else str(resposta)
        except json.JSONDecodeError:
            # Si no és JSON vàlid, tractem la resposta com a ID directament
            puzzle_id = resposta_raw.strip()
 
        return puzzle_id
 
    except urllib.error.HTTPError as e:
        # Es llegeix el cos de l'error per mostrar el missatge del servidor
        detall = e.read().decode() if e.fp else ""
        print(f"Error HTTP {e.code} en enviar el puzzle: {e.reason}")
        if detall:
            print(f"Detall: {detall}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error de connexió: {e.reason}")
        sys.exit(1)
 
 
# Flux principal
 
def pujar_puzzle(puzzle_path: Path, token: str) -> None:
    """
    Orquestra el flux complet: lectura del fitxer, avaluació matemàtica i enviament.
    
    Pre: 'puzzle_path' apunta a un fitxer local existent amb extensió .json i format vàlid.
         'token' és una cadena de text per a l'autenticació.
    Post: S'instancia el puzzle, s'hi aplica eval.py mostrant-ne els resultats per terminal, 
          i finalment s'envia a l'API. Imprimeix l'ID assignat un cop finalitzat.
    """

    # Pas 1: lectura i validació del fitxer local
    print(f"Llegint puzzle des de '{puzzle_path}'...")
    try:
        pz = Puzzle.from_json(puzzle_path.read_text())  # ValueError si el format és incorrecte
    except (ValueError, KeyError) as e:
        print(f"Error en llegir el puzzle: {e}")
        sys.exit(1)
 
    print(f"Puzzle vàlid: {pz.W}×{pz.H}, {len(pz.pieces)} peces, {len(pz.goals)} objectiu(s)")
 
    # Pas 2: avaluació automàtica per informar l'usuari de la qualitat del puzzle
    print("\nAvaluant el puzzle abans d'enviar...")
    resultat = avaluar_puzzle(pz)
    imprimir_avaluacio(pz, resultat)
 
    # Si la puntuació és baixa, s'avisa a l'usuari, però no interromp la publicació del puzzle
    if resultat["puntuacio"] < 1.0:
        print("\n⚠️  Advertència: la puntuació és baixa (< 1.0). El puzzle pot ser poc interessant.")
        print("   Continuant l'enviament igualment...")
 
    # Pas 3: enviament al repositori
    print(f"\nEnviant puzzle al repositori ({BASE_URL})...")
    puzzle_id = enviar_puzzle(pz, token)
 
    print(f"\n✓ Puzzle enviat correctament!")
    print(f"  ID assignat: {puzzle_id}")
    print(f"  Puntuació:   {resultat['puntuacio']:.2f} / 5.00")
 
# Punt d'entrada
 
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
 
    # Comprovem que el fitxer existeix abans de fer res
    if not args.puzzle.exists():
        print(f"Error: no s'ha trobat el fitxer '{args.puzzle}'")
        sys.exit(1)
 
    pujar_puzzle(args.puzzle, args.token)
 