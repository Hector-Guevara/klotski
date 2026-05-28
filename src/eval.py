"""
Avalua un puzzle de peces lliscants mesurant l'interès del seu graf d'estats.
 
La puntuació final (de 0.0 a 5.0) combina cinc mètriques del graf:
  1. Longitud de la solució òptima  (més moviments → més difícil)
  2. Mida de l'espai d'estats       (més estats accessibles → més complex)
  3. Unicitat de la solució         (menys solucions → menys trivial)
  4. Eficiència del camí òptim      (camí profund en espai dens → interessant)
  5. Ponts estructurals al graf     (colls d'ampolla → el puzzle té "fases")
 
Estratègia de velocitat:
  - El graf es genera amb un límit de LIMIT_ESTATS nodes. Si el puzzle és
    gran, el graf es talla i les mètriques d'espai/ponts es saturen a 1.0
    (comportament correcte: un puzzle amb >LIMIT_ESTATS estats és màxim).
  - La longitud òptima s'obté sempre amb shortest_distance sobre el graf
    parcial. Si el node destí no és assolible dins del límit, es fa servir
    l'A* de solve.py com a fallback.
 
Ús: 
    python3 eval.py <puzzle.json>
"""
 
from __future__ import annotations
 
import math
import sys
from pathlib import Path
 
import graph_tool.all as gt  # type: ignore[import-untyped]
 
from graph import generar_graf
from puzzle import Puzzle
from solve import _a_star_real
 
 
# Pesos de cada mètrica (han de sumar 1.0)
 
PES_LONGITUD_SOLUCIO = 0.35
PES_ESPAI_ESTATS     = 0.25
PES_UNICITAT_SOLUCIO = 0.20
PES_EFICIENCIA_CAMI  = 0.10
PES_PONTS            = 0.10
 
# Llindars de referència i límit d'exploració
 
LONGITUD_MAX_REF = 90
ESTATS_MAX_REF   = 200_000
PONTS_MAX_REF    = 20
 
# Límit d'estats per al graf: per sobre d'aquest valor les mètriques d'espai i ponts ja obtenen la puntuació màxima
LIMIT_ESTATS = 200_000
 
 
# Mètriques individuals
 
def _normalitzar(valor: float, maxim: float) -> float:
    """
    Escala un valor linealment assegurant que quedi acotat entre 0.0 i 1.0.
    
    Pre: 'valor' >= 0, 'maxim' > 0.
    Post: Retorna un float a l'interval [0.0, 1.0].
    """    

    if maxim <= 0:
        return 0.0
    return min(valor / maxim, 1.0)
 
 
def score_longitud(longitud_optima: int) -> float:
    """
    Avalua la dificultat basada en la quantitat de moviments per resoldre'l.
    
    Pre: 'longitud_optima' >= 0.
    Post: Retorna la puntuació normalitzada [0.0, 1.0].
    """

    return _normalitzar(longitud_optima, LONGITUD_MAX_REF)
 
 
def score_espai(num_estats: int) -> float:
    """
    Avalua la complexitat de l'espai d'estats (possibles estats del puzzle, és a dir, nodes del graf).
    
    Pre: 'num_estats' >= 0.
    Post: Retorna la puntuació normalitzada [0.0, 1.0].
    """
    return _normalitzar(num_estats, ESTATS_MAX_REF)
 
 
def score_unicitat(num_solucions: int) -> float:
    """
    Premia els puzzles amb poques solucions, on el jugador no pot resoldre'l "per casualitat".
    És a dir, premia els puzzles que tenen pocs camins possibles fins arribar a la solució.
    Usa una escala logarítmica invertida per penalitzar ràpidament l'excés de solucions.
    
    Pre: 'num_solucions' >= 0.
    Post: Retorna un valor [0.0, 1.0]. Retorna 1.0 si només hi ha 1 solució.
    """
    if num_solucions <= 0:
        return 0.0
    return 1.0 / math.log2(1 + num_solucions)
 
 
def score_eficiencia(longitud_optima: int, num_estats: int) -> float:
    """
    Mesura la profunditat del camí respecte a la mida del graf. Un puzzle on
    cal explorar gairebé tots els estats per trobar la solució és molt eficient.
    
    Pre: 'longitud_optima' >= 0 i 'num_estats' >= 0.
    Post: Retorna un valor [0.0, 1.0] basat en la relació logarítmica de profunditat.
    """
    if num_estats <= 0 or longitud_optima <= 0:
        return 0.0
    return math.log2(1 + longitud_optima) / math.log2(1 + num_estats)
 
 
def score_ponts(g: gt.Graph) -> float:
    """
    Avalua la presència de "colls d'ampolla" al graf. Les arestes pont representen
    moviments obligatoris (si no es fan, és impossible arribar a la solució).
    
    Pre: 'g' és un objecte Graph vàlid de graph_tool.
    Post: Retorna la puntuació normalitzada [0.0, 1.0] depenent de la quantitat de ponts.
    """
    g_no_dir = gt.GraphView(g, directed=False)
    _, arestes_pont, _ = gt.label_biconnected_components(g_no_dir)
    num_ponts = int(arestes_pont.a.sum())
    return _normalitzar(num_ponts, PONTS_MAX_REF)
 
 
# Funció principal d'avaluació
 
def avaluar_puzzle(pz: Puzzle, limit_estats: int | None = LIMIT_ESTATS) -> dict:
    """
    Calcula de forma eficient totes les mètriques d'un puzzle i en retorna la nota final.
    
    Intenta resoldre'l primer creant un graf parcial. 
    Si la solució queda fora del límit de generació de nodes, salta a un A* pur per trobar-la.
    Pot tenir límit d'estats opcional també en la resolució del A*, per evitar possibles bloquejos
    
    Pre: 'pz' és un Puzzle vàlid. 'limit_estats' és un enter positiu o None.
    Post: Retorna un diccionari amb les dades de resolubilitat, els valors absoluts 
          de cada mètrica, les puntuacions parcials [0.0, 1.0] i la nota final [0.0, 5.0].
    """
    # Graf parcial
    g, nodes_desti = generar_graf(pz, limit_estats=limit_estats)
 
    num_estats    = g.num_vertices()
    num_solucions = len(nodes_desti)
 
    # Longitud òptima
    longitud_optima = 0
    resoluble = False
 
    if nodes_desti:
        # Primer cas: el node destí és dins del graf parcial (tallat a 200.000 estats)
        node_inicial = gt.find_vertex(g, g.vp["is_start"], True)[0]
        distancies = gt.shortest_distance(g, source=node_inicial)
        INF = 2**31 - 1
        dist_min = min(int(distancies[d]) for d in nodes_desti)
        if dist_min < INF:
            longitud_optima = dist_min
            resoluble = True
 
    if not resoluble:
        # Segon cas: el graf s'ha tallat abans d'arribar al destí.
        # S'explora aprofitant l'algorisme A* de solve.py
        cami = _a_star_real(pz, max_estats=limit_estats)
        if cami is not None:
            longitud_optima = len(cami)
            resoluble = True
            
            # Només saturem l'espai si hi havia un límit imposat
            if limit_estats is not None:
                num_estats = max(num_estats, limit_estats)
                
            # num_solucions del graf parcial és 0, però el puzzle és resoluble;
            # posem 1 com a estimació conservadora (pitjor cas per a unicitat)
            if num_solucions == 0:
                num_solucions = 1
 
    if not resoluble:
        return {
            "resoluble":       False,
            "num_estats":      num_estats,
            "num_solucions":   0,
            "longitud_optima": 0,
            "scores": {
                "longitud":   0.0,
                "espai":      score_espai(num_estats),
                "unicitat":   0.0,
                "eficiencia": 0.0,
                "ponts":      score_ponts(g),
            },
            "puntuacio": 0.0,
        }
 
    # Mètriques
    s_longitud   = score_longitud(longitud_optima)
    s_espai      = score_espai(num_estats)
    s_unicitat   = score_unicitat(num_solucions)
    s_eficiencia = score_eficiencia(longitud_optima, num_estats)
    s_ponts      = score_ponts(g)
 
    puntuacio_norm = (
        PES_LONGITUD_SOLUCIO * s_longitud   +
        PES_ESPAI_ESTATS     * s_espai      +
        PES_UNICITAT_SOLUCIO * s_unicitat   +
        PES_EFICIENCIA_CAMI  * s_eficiencia +
        PES_PONTS            * s_ponts
    )
    puntuacio = round(puntuacio_norm * 5.0, 2)
 
    return {
        "resoluble":       True,
        "num_estats":      num_estats,
        "num_solucions":   num_solucions,
        "longitud_optima": longitud_optima,
        "scores": {
            "longitud":   round(s_longitud,   3),
            "espai":      round(s_espai,      3),
            "unicitat":   round(s_unicitat,   3),
            "eficiencia": round(s_eficiencia, 3),
            "ponts":      round(s_ponts,      3),
        },
        "puntuacio": puntuacio,
    }
 
 
# Impressió del resultat
 
def imprimir_avaluacio(pz: Puzzle, resultat: dict) -> None:
    """
    Donat un puzzle, i el resultat de la seva evaluació, imprimeix les puntuacions
    i les dades en el format desitjat. Aquestes dades són la mida del taulell, el
    nombre de peces, si és resoluble, el nombre d'estats totals, el nombre de nodes
    que són solució, la longitud òptima per resoldre'l i una representació gràfica
    de les mètriques prèviament calculades.
    """
    print(f"Taulell:          {pz.W}x{pz.H}  ({len(pz.pieces)} peces)")
    print(f"Resoluble:        {'Sí' if resultat['resoluble'] else 'No'}")
    print(f"Estats totals:    {resultat['num_estats']}")  # pot ser > 200.000, però aquest serà el valor màxim que retorni
    print(f"Solucions (dest): {resultat['num_solucions']}")
    print(f"Longitud òptima:  {resultat['longitud_optima']} moviments")
    print()
    print("Mètriques parcials (0-1):")
    for nom, val in resultat["scores"].items():
        barra = "█" * int(val * 20)
        print(f"  {nom:<12} {val:.3f}  {barra}")
    print()
    print(f"Puntuació final:  {resultat['puntuacio']:.2f} / 5.00  {'⭐' * round(resultat['puntuacio'])}")
 
 
# Punt d'entrada
 
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Ús: python3 {sys.argv[0]} <puzzle.json>")
        sys.exit(1)
 
    puzzle_path = Path(sys.argv[1])
    pz = Puzzle.from_json(puzzle_path.read_text())
 
    resultat = avaluar_puzzle(pz)
    imprimir_avaluacio(pz, resultat)