"""
Avalua un puzzle del repositori i n'envia la valoració (0-5 estrelles reals com a enters).
 
El flux és el següent:
  1. Descarrega el puzzle per ID des del repositori.
  2. Calcula la puntuació automàtica amb eval.py.
  3. Envia la valoració al repositori via POST autenticat amb el token.
 
Ús:
    python3 rate.py <puzzle_id> <token>
    python3 rate.py <puzzle_id> <token> [--puntuacio <0-5>]
 
Si no s'especifica --puntuacio, es fa servir la valoració calculada per eval.py (arrodonida a enter).
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
# Configuració del repositori (mateixa base que download.py)
# ---------------------------------------------------------------------------
 
BASE_URL = "https://klotski.pauek.dev/api/puzzles"
 
 
# ---------------------------------------------------------------------------
# Funcions de comunicació amb el repositori
# ---------------------------------------------------------------------------
 
def descarregar_puzzle(puzzle_id: str) -> Puzzle:
    """
    Descarrega un puzzle del repositori donat el seu ID.
    El servidor retorna {"puzzle": {...}, "stars": N}; s'extreu només la part del puzzle.
    Retorna l'objecte Puzzle ja parsejat.
    """
    url = f"{BASE_URL}/{puzzle_id}"
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"Error HTTP {e.code} en descarregar el puzzle '{puzzle_id}': {e.reason}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error de connexió: {e.reason}")
        sys.exit(1)
 
    # el servidor embolcalla el puzzle: {"puzzle": {...}, "stars": 4.4}
    puzzle_data = data["puzzle"] if "puzzle" in data else data
    return Puzzle.from_json(json.dumps(puzzle_data))
 
 
def enviar_valoracio(puzzle_id: str, token: str, puntuacio: int) -> None:
    """
    Envia una valoració (0-5 com a enter) al repositori per al puzzle indicat.
    Fa servir una petició POST autenticada amb el token Bearer.
    """
    url = f"{BASE_URL}/{puzzle_id}/votes"
 
    # CORRECCIÓ: Cambiamos la clave "score" por "stars" que es la que pide el servidor
    cos = json.dumps({"stars": puntuacio}).encode()
 
    # es crea la petició amb el token d'autenticació a la capçalera
    peticio = urllib.request.Request(
        url,
        data=cos,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
 
    try:
        with urllib.request.urlopen(peticio) as response:
            resposta = response.read().decode()
            print(f"Valoració enviada correctament: {resposta}")
    except urllib.error.HTTPError as e:
        # es llegeix el cos de l'error per mostrar el missatge del servidor
        detall = e.read().decode() if e.fp else ""
        print(f"Error HTTP {e.code} en enviar la valoració: {e.reason}")
        if detall:
            print(f"Detall: {detall}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error de connexió: {e.reason}")
        sys.exit(1)
 
 
# ---------------------------------------------------------------------------
# Flux principal
# ---------------------------------------------------------------------------
 
def valorar_puzzle(puzzle_id: str, token: str, puntuacio_manual: int | None) -> None:
    """
    Orquestra el flux complet: descarrega, avalua i envia la valoració com a enter.
    Si puntuacio_manual és None, es fa servir la puntuació calculada per eval.py arrodonida.
    """
 
    # pas 1: descarrega del repositori
    print(f"Descarregant puzzle '{puzzle_id}'...")
    pz = descarregar_puzzle(puzzle_id)
 
    # pas 2: avaluació automàtica (sempre es calcula per mostrar-la)
    print("Avaluant el puzzle...")
    resultat = avaluar_puzzle(pz)
    imprimir_avaluacio(pz, resultat)
 
    # pas 3: es decideix quina puntuació s'envia (garantint ENTERS)
    if puntuacio_manual is not None:
        # l'usuari ha sobreescrit la puntuació manualment (ja és un int gràcies a argparse)
        puntuacio_final = max(0, min(5, puntuacio_manual))
        print(f"\nPuntuació manual especificada: {puntuacio_final} / 5")
    else:
        # es fa servir la puntuació calculada per eval.py i es força a enter (arrodonint)
        puntuacio_final = round(resultat["puntuacio"])
        puntuacio_final = max(0, min(5, puntuacio_final))
        print(f"\nPuntuació automàtica (eval.py, arrodonida): {puntuacio_final} / 5")
 
    # pas 4: enviament al repositori
    print(f"Enviant valoració al repositori...")
    enviar_valoracio(puzzle_id, token, puntuacio_final)
 
 
# ---------------------------------------------------------------------------
# Punt d'entrada
# ---------------------------------------------------------------------------
 
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Avalua un puzzle del repositori i n'envia la valoració (enters de 0 a 5)."
    )
    parser.add_argument(
        "puzzle_id",
        help="Identificador del puzzle al repositori",
    )
    parser.add_argument(
        "token",
        help="Token d'autenticació Bearer per enviar valoracions",
    )
    parser.add_argument(
        "--puntuacio",
        type=int,
        default=None,
        metavar="N",
        help="Puntuació manual sencera (0-5). Si no s'especifica, es fa servir eval.py",
    )
 
    args = parser.parse_args()
 
    valorar_puzzle(args.puzzle_id, args.token, args.puntuacio)