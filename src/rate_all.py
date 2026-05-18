"""
Avalua d'una sola passada tots els puzzles presents en el repositori i n'envia la valoració.

El flux és el següent:
  1. Descarrega la llista de tots els IDs des del repositori.
  2. Per a cada puzzle, delega en `valorar_puzzle` de rate.py (descarrega, avalua i envia).

Ús:
    python3 rate_all.py <token>
    python3 rate_all.py <token> --puntuacio N   # força la mateixa nota a tots
    python3 rate_all.py <token> --skip-errors   # continua si algun puzzle falla
"""

from __future__ import annotations

import sys
import json
import argparse
import urllib.request
import urllib.error

from rate import valorar_puzzle

# ---------------------------------------------------------------------------
# Configuració del repositori
# ---------------------------------------------------------------------------

BASE_URL = "https://klotski.pauek.dev/api/puzzles"


# ---------------------------------------------------------------------------
# Llista de puzzles
# ---------------------------------------------------------------------------

def descarregar_llista_puzzles() -> list[str]:
    """
    Retorna la llista de tots els IDs de puzzles disponibles al repositori.
    El servidor respon amb un array JSON de strings: ["id1", "id2", ...].
    """
    try:
        with urllib.request.urlopen(BASE_URL) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"Error HTTP {e.code} en obtenir la llista de puzzles: {e.reason}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error de connexió: {e.reason}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Flux principal
# ---------------------------------------------------------------------------

def valorar_tots(token: str, puntuacio_manual: int | None, skip_errors: bool) -> None:
    """
    Descarrega la llista completa de puzzles i avalua/valora cadascun
    delegant en `valorar_puzzle` de rate.py.
    """
    print("Obtenint la llista de puzzles del repositori...")
    ids = descarregar_llista_puzzles()
    total = len(ids)
    print(f"S'han trobat {total} puzzle(s).\n")

    errors: list[tuple[str, str]] = []

    for i, puzzle_id in enumerate(ids, start=1):
        print(f"─── [{i}/{total}] Puzzle: {puzzle_id[:12]}... ───")
        try:
            valorar_puzzle(puzzle_id, token, puntuacio_manual)
        except SystemExit:
            # valorar_puzzle fa sys.exit(1) en cas d'error; el capturem per poder continuar
            msg = "error durant la descàrrega, avaluació o enviament (vegeu el missatge anterior)"
            errors.append((puzzle_id, msg))
            if not skip_errors:
                print("\nAturant per error. Usa --skip-errors per continuar malgrat els errors.")
                sys.exit(1)
        except Exception as exc:
            msg = str(exc)
            print(f"  ERROR inesperat: {msg}")
            errors.append((puzzle_id, msg))
            if not skip_errors:
                sys.exit(1)
        print()

    # Resum final
    ok = total - len(errors)
    print(f"════ Resum: {ok}/{total} puzzles valorats correctament ════")
    if errors:
        print(f"Errors ({len(errors)}):")
        for pid, msg in errors:
            print(f"  • {pid[:12]}... → {msg}")


# ---------------------------------------------------------------------------
# Punt d'entrada
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Avalua TOTS els puzzles del repositori i n'envia la valoració (0-5)."
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
        help="Puntuació manual sencera (0-5) igual per a tots. "
             "Si no s'especifica, es fa servir eval.py per a cadascun.",
    )
    parser.add_argument(
        "--skip-errors",
        action="store_true",
        help="Continua amb el següent puzzle si n'hi ha algun que falla.",
    )

    args = parser.parse_args()
    valorar_tots(args.token, args.puntuacio, args.skip_errors)