import urllib.request
import json
import os

BASE_URL = "https://klotski.pauek.dev/api/puzzles"
DEST_FOLDER = "puzzles"

def get_json(url):
    """
    Funció per obtenir l'arxiu JSON d'un enllaç donat.
    """
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read().decode())

def download_all():
    """
    Descarrega tots els puzzles que hi hagi en la BASE_URL donada.
    Per utilitzar-se: python src/download.py
    """

    # en cas que la carpeta per guardar els puzzles no existeixi
    if not os.path.exists(DEST_FOLDER):
        os.makedirs(DEST_FOLDER)

    try:
        # s'obtenen totes les direccions ID de la pàgina web
        print("Obteniendo lista de IDs...")
        puzzle_ids = get_json(BASE_URL)
        i = 1  # inicialitzem, per posar el nom que calgui
        print(f"S'han trobat {len(puzzle_ids)} puzzles. Inicialitzant la descàrrega...")

        # es descarreguen tots els puzzles
        for p_id in puzzle_ids:
            file_path = os.path.join(DEST_FOLDER, f"puzzle_{i}.json")
            
            # si ja està instal·lat, es passa al següent
            if os.path.exists(file_path):
                continue
            
            # descarrega el puzzle donada la seva ID, accedint a la pàgina: https://klotski.pauek.dev/api/puzzles/[id]
            puzzle_data = get_json(f"{BASE_URL}/{p_id}")
            
            with open(file_path, 'w') as f:
                json.dump(puzzle_data, f, indent=4)
            
            i += 1

        print("Tots els fitxers descarregats i disponibles a la carpeta puzzles.")

    except Exception as e:
        print(f"\nError: {e}")
        
if __name__ == "__main__":
    download_all()