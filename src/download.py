"""
Descarrega els puzzles des del repositori compartit.

Pot descarregar-ne tots els puzzles de cop, o descarregar-ne un en concret si es dona la direcció ID del puzzle en el repositori.

Ús:
    python3 download.py
    python3 download.py <puzzle_id>
"""

import urllib.request
import json
import os
import sys

BASE_URL = "https://klotski.pauek.dev/api/puzzles"
DEST_FOLDER = "puzzles"

def get_json(url: str):
    """
    Funció per obtenir l'arxiu JSON d'un enllaç (url) donat.
    Descarrega el puzzle del repositori que correspon a aquell arxiu.
    Pre: 'url' és una cadena de text amb una URL vàlida i accessible que 
    retorna contingut en format JSON.
    Post: Retorna les dades del JSON parsejades (habitualment un dict o list).
    """
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read().decode())

def extreure_puzzle(data: dict) -> dict:
    """
    El servidor retorna els puzzles embolcallats: {"puzzle": {...}, "stars": 4.4}.
    Aquesta funció extreu només la part del puzzle per guardar-la en format estàndard.
    Si la resposta ja és un puzzle directe (format antic), la retorna tal qual.
    """
    if "puzzle" in data:
        return data["puzzle"]
    return data

def download_one(puzzle_id: str) -> None:
    """
    Descarrega un únic puzzle específic mitjançant el seu ID.
    El guarda a la carpeta DEST_FOLDER ("puzzles") amb el nom del seu ID.
    Crea la carpeta en cas que no hi sigui.
    """
    if not os.path.exists(DEST_FOLDER):
        os.makedirs(DEST_FOLDER)

    file_path = os.path.join(DEST_FOLDER, f"puzzle_{puzzle_id}.json")

    try:
        print(f"Descarregant el puzzle únic amb ID: {puzzle_id}...")
        raw = get_json(f"{BASE_URL}/{puzzle_id}")
        puzzle_data = extreure_puzzle(raw)

        with open(file_path, 'w') as f:
            json.dump(puzzle_data, f, indent=4)

        print(f"Puzzle descarregat correctament a: {file_path}")

    except urllib.error.HTTPError as e:
        print(f"Error HTTP {e.code}: No s'ha trobat cap puzzle amb l'ID '{puzzle_id}' al servidor.")
    except Exception as e:
        print(f"Error en descarregar el puzzle únic: {e}")

def download_all() -> None:
    """
    Descarrega un puzzle específic mitjançant el seu ID i el desa localment.
    
    Pre: 'puzzle_id' és un string vàlid que correspon a un puzzle existent al servidor.
    Post: El puzzle s'ha desat a DEST_FOLDER amb el nom 'puzzle_<puzzle_id>.json'.
          Si la carpeta no existeix, es crea automàticament. En cas d'error de xarxa,
          s'informa per la sortida estàndard.
    """

    # en cas que la carpeta per guardar els puzzles no existeixi
    if not os.path.exists(DEST_FOLDER):
        os.makedirs(DEST_FOLDER)

    try:
        # s'obtenen totes les direccions ID de la pàgina web
        print("Obtenint llista d'IDs...")
        puzzle_ids = get_json(BASE_URL)
        i = 1  # inicialitzem, per posar el nom que calgui
        print(f"S'han trobat {len(puzzle_ids)} puzzles. Inicialitzant la descàrrega...")

        # es descarreguen tots els puzzles
        for p_id in puzzle_ids:
            file_path = os.path.join(DEST_FOLDER, f"puzzle_{i:03d}.json")
            
            # si ja està instal·lat, es passa al següent
            if os.path.exists(file_path):
                i += 1
                continue
            
            # descarrega el puzzle donada la seva ID i extreu la part del puzzle
            raw = get_json(f"{BASE_URL}/{p_id}")
            puzzle_data = extreure_puzzle(raw)
            
            with open(file_path, 'w') as f:
                json.dump(puzzle_data, f, indent=4)
            
            i += 1

        print("Tots els fitxers descarregats i disponibles a la carpeta puzzles.")

    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    # Si l'usuari passa un argument extra (l'ID del puzzle)
    if len(sys.argv) > 1:
        puzzle_id_argument = sys.argv[1]
        download_one(puzzle_id_argument)
    else:
        # Si no hi ha cap argument, es fa la descàrrega massiva habitual
        download_all()