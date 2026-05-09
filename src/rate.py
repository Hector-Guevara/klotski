"""
Avalua un puzzle del repositori i n'envia la valoració (0.0–5.0 estrelles).

El flux és el següent:
  1. Descarrega el puzzle per ID des del repositori.
  2. Calcula la puntuació automàtica amb eval.py.
  3. Envia la valoració al repositori via POST autenticat amb el token.

Ús:
    python3 rate.py <puzzle_id> <token>
    python3 rate.py <puzzle_id> <token> [--puntuacio <0.0-5.0>]

Si no s'especifica --puntuacio, es fa servir la valoració calculada per eval.py.
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
    Retorna l'objecte Puzzle ja parsejat.
    """
    url = f"{BASE_URL}/{puzzle_id}"
    try:
        with urllib.request.urlopen(url) as response:
            contingut = response.read().decode()
    except urllib.error.HTTPError as e:
        print(f"Error HTTP {e.code} en descarregar el puzzle '{puzzle_id}': {e.reason}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error de connexió: {e.reason}")
        sys.exit(1)

    return Puzzle.from_json(contingut)


def enviar_valoracio(puzzle_id: str, token: str, puntuacio: float) -> None:
    """
    Envia una valoració (0.0–5.0) al repositori per al puzzle indicat.
    Fa servir una petició POST autenticada amb el token Bearer.
    """
    url = f"{BASE_URL}/{puzzle_id}/votes"

    # es construeix el cos de la petició en format JSON
    cos = json.dumps({"score": puntuacio}).encode()

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

def valorar_puzzle(puzzle_id: str, token: str, puntuacio_manual: float | None) -> None:
    """
    Orquestra el flux complet: descarrega, avalua i envia la valoració.
    Si puntuacio_manual és None, es fa servir la puntuació calculada per eval.py.
    """

    # pas 1: descarrega del repositori
    print(f"Descarregant puzzle '{puzzle_id}'...")
    pz = descarregar_puzzle(puzzle_id)

    # pas 2: avaluació automàtica (sempre es calcula per mostrar-la)
    print("Avaluant el puzzle...")
    resultat = avaluar_puzzle(pz)
    imprimir_avaluacio(pz, resultat)

    # pas 3: es decideix quina puntuació s'envia
    if puntuacio_manual is not None:
        # l'usuari ha sobreescrit la puntuació manualment
        puntuacio_final = max(0.0, min(5.0, puntuacio_manual))
        print(f"\nPuntuació manual especificada: {puntuacio_final:.2f} / 5.00")
    else:
        # es fa servir la puntuació calculada per eval.py
        puntuacio_final = resultat["puntuacio"]
        print(f"\nPuntuació automàtica (eval.py): {puntuacio_final:.2f} / 5.00")

    # pas 4: enviament al repositori
    print(f"Enviant valoració al repositori...")
    enviar_valoracio(puzzle_id, token, puntuacio_final)


# ---------------------------------------------------------------------------
# Punt d'entrada
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Avalua un puzzle del repositori i n'envia la valoració."
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
        type=float,
        default=None,
        metavar="N",
        help="Puntuació manual (0.0–5.0). Si no s'especifica, es fa servir eval.py",
    )

    args = parser.parse_args()

    valorar_puzzle(args.puzzle_id, args.token, args.puntuacio)
