"""
Avalua un puzzle del repositori i n'envia la valoració (0-5 estrelles reals com a enters).
 
El flux és el següent:
  1. Descarrega el puzzle per ID des del repositori.
  2. Calcula la puntuació automàtica amb eval.py (sense límit d'estats).
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
 
from puzzle import Puzzle
from eval import avaluar_puzzle, imprimir_avaluacio
from download import BASE_URL 
 
# Funcions de comunicació amb el repositori
 
def descarregar_puzzle(puzzle_id: str) -> Puzzle:
    """
    Descarrega i parseja un puzzle específic del repositori mitjançant el seu ID.
    
    Pre: 'puzzle_id' és un identificador vàlid (string) d'un puzzle existent al servidor.
    Post: Retorna un objecte Puzzle instanciat amb les dades obtingudes. Si hi ha un error 
          de xarxa o el puzzle no existeix (HTTP 404), l'script s'atura amb sys.exit(1).
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
 
    # El servidor embolcalla el puzzle: {"puzzle": {...}, "stars": 4.4}
    puzzle_data = data["puzzle"] if "puzzle" in data else data
    return Puzzle.from_json(json.dumps(puzzle_data))
 
 
def enviar_valoracio(puzzle_id: str, token: str, puntuacio: int) -> None:
    """
    Envia la puntuació final d'un puzzle al servidor mitjançant una petició POST.
    
    Pre: 'puzzle_id' és vàlid, 'token' és un string d'autenticació Bearer actiu, 
          i 'puntuacio' és un enter acotat entre 0 i 5.
    Post: La valoració queda registrada al servidor. En cas d'error (token invàlid HTTP 401, 
          sense connexió, etc.), es mostra el missatge d'error detallat i s'atura l'execució.
    """
    url = f"{BASE_URL}/{puzzle_id}/votes"
 
    cos = json.dumps({"stars": puntuacio}).encode()
 
    # Es crea la petició amb el token d'autenticació a la capçalera
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
        # Es llegeix el cos de l'error per mostrar el missatge del servidor
        detall = e.read().decode() if e.fp else ""
        print(f"Error HTTP {e.code} en enviar la valoració: {e.reason}")
        if detall:
            print(f"Detall: {detall}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error de connexió: {e.reason}")
        sys.exit(1)
 
 
# Flux principal
 
def valorar_puzzle(puzzle_id: str, token: str, puntuacio_manual: int | None) -> None:
    """
    Orquestra el flux complet per a un sol puzzle: el descarrega, n'avalua la 
    dificultat de forma exhaustiva (sense límit d'estats) i n'envia la nota final.
    Pot donar-se una puntuació manualment en 'puntuacio_manual', que és la que
    s'utilitzarà. En cas contrari, s'utilitza la valoració generada per eval.py
    
    Pre: 'puzzle_id' i 'token' són cadenes de text vàlides. 'puntuacio_manual' pot 
         ser un enter o bé None si es desitja fer servir el càlcul automàtic.
    Post: El puzzle ha estat avaluat completament (el procés pot ser llarg si el graf 
          és molt complex) i la seva nota ha estat enviada al repositori en format enter.
    """
 
    # Pas 1: descarrega del repositori
    print(f"Descarregant puzzle '{puzzle_id}'...")
    pz = descarregar_puzzle(puzzle_id)
 
    # Pas 2: avaluació automàtica (sense límit d'estats perquè avaluï completament)
    print("Avaluant el puzzle (sense límit, pot trigar si és molt complex)...")
    resultat = avaluar_puzzle(pz, limit_estats=None)
    imprimir_avaluacio(pz, resultat)
 
    # Pas 3: es decideix quina puntuació s'envia (garantint enters)
    if puntuacio_manual is not None:
        # L'usuari ha sobreescrit la puntuació manualment (ja és un int gràcies a argparse)
        puntuacio_final = max(0, min(5, puntuacio_manual))
        print(f"\nPuntuació manual especificada: {puntuacio_final} / 5")
    else:
        # Es fa servir la puntuació calculada per eval.py i es força a enter (arrodonint)
        puntuacio_final = round(resultat["puntuacio"])
        puntuacio_final = max(0, min(5, puntuacio_final))
        print(f"\nPuntuació automàtica (eval.py, arrodonida): {puntuacio_final} / 5")
 
    # Pas 4: enviament al repositori
    print(f"Enviant valoració al repositori...")
    enviar_valoracio(puzzle_id, token, puntuacio_final)
 
 
# Punt d'entrada
 
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