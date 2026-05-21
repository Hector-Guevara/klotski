"""
Avalua un puzzle de peces lliscants mesurant l'interès del seu graf d'estats.
 
La puntuació final (de 0.0 a 5.0) combina cinc mètriques del graf:
 
  1. Longitud de la solució òptima  (més moviments → més difícil)
  2. Mida de l'espai d'estats       (més estats accessibles → més complex)
  3. Unicitat de la solució         (menys solucions → més difícil)
  4. Eficiència del camí òptim      (camí llarg sobre espai dens → més interessant)
  5. Ponts estructurals al graf     (colls d'ampolla → el puzzle té "fases")
 
Arquitectura de dues passades independent:
  - Passada 1 (graf)  → generar_graf sense límit artificial, extreu mètriques
                        estructurals (num_estats, num_solucions, ponts).
  - Passada 2 (A*)    → _a_star_real, obté la longitud òptima exacta sense
                        dependre del graf.
 
  Les dues passades són completament independents: si el graf és gran, les
  mètriques d'espai i ponts es saturen a 1.0 igualment (per disseny dels
  llindars), i la mètrica de longitud segueix sent exacta gràcies a l'A*.
 
Ús: python3 eval.py <puzzle.json>
"""
 
from __future__ import annotations
 
import math
import sys
from pathlib import Path
 
import graph_tool.all as gt  # type: ignore[import-untyped]
 
from graph import generar_graf
from puzzle import Puzzle
from solve import _a_star_real
 
 
# ---------------------------------------------------------------------------
# Pesos de cada mètrica (han de sumar 1.0)
# ---------------------------------------------------------------------------
 
PES_LONGITUD_SOLUCIO = 0.35  # mètrica principal de dificultat
PES_ESPAI_ESTATS     = 0.25  # recompensa espais de cerca grans
PES_UNICITAT_SOLUCIO = 0.20  # penalitza puzzles amb moltes solucions trivials
PES_EFICIENCIA_CAMI  = 0.10  # recompensa que el camí òptim sigui "profund"
PES_PONTS            = 0.10  # recompensa l'existència de fases al puzzle


# ---------------------------------------------------------------------------
# Llindars de referència per a la normalització lineal saturada a [0, 1].
#
# Criteris de calibratge (observats sobre puzzles de mostra):
#   LONGITUD_MAX_REF : klotski original té ~116 moviments; 90 és un llindar
#                      realista per als puzzles generats (mides 4-7x4-7).
#   ESTATS_MAX_REF   : klotski i variants densos generen ~50.000-150.000 estats.
#                      35.000 satura ràpid puzzles hard i dona bon gradient als
#                      puzzles medium/easy.
#   PONTS_MAX_REF    : més de 20 ponts estructurals indica un puzzle molt segmentat;
#                      per sobre d'aquest valor la mètrica ja no discrimina més.
# ---------------------------------------------------------------------------
 
LONGITUD_MAX_REF = 90
ESTATS_MAX_REF   = 35_000
PONTS_MAX_REF    = 20
 
 
# ---------------------------------------------------------------------------
# Mètriques individuals
# ---------------------------------------------------------------------------
 
def _normalitzar(valor: float, maxim: float) -> float:
    """Saturació lineal a [0, 1]: valor/maxim, amb cap a 1.0."""
    if maxim <= 0:
        return 0.0
    return min(valor / maxim, 1.0)
 
 
def score_longitud(longitud_optima: int) -> float:
    """
    Mètrica 1 — Longitud de la solució òptima.
    Creix linealment fins a LONGITUD_MAX_REF i satura a 1.0.
    """
    return _normalitzar(longitud_optima, LONGITUD_MAX_REF)
 
 
def score_espai(num_estats: int) -> float:
    """
    Mètrica 2 — Mida de l'espai d'estats accessibles.
    Creix linealment fins a ESTATS_MAX_REF i satura a 1.0.
    Nota: si el graf s'ha explorat parcialment, num_estats és un mínim;
    la saturació assegura que puzzles molt grans rebin 1.0 igualment.
    """
    return _normalitzar(num_estats, ESTATS_MAX_REF)
 
 
def score_unicitat(num_solucions: int) -> float:
    """
    Mètrica 3 — Unicitat de la solució.
    Usa log2 perquè: 1 solució → 1.0, 2 → 0.5, 4 → 0.33, 8 → 0.25 ...
    Amb log (base e) l'escala seria diferent: 1 → ∞ (divisió per zero si
    s'usa log(1+n) amb n=0), i log(2) ≈ 0.69, de manera que 1 solució
    donaria 1/0.69 > 1 (fora de [0,1]). log2 és l'única base que garanteix
    exactament 1.0 per a 1 solució sense cap factor d'escala addicional.
    """
    if num_solucions <= 0:
        return 0.0
    return 1.0 / math.log2(1 + num_solucions)
 
 
def score_eficiencia(longitud_optima: int, num_estats: int) -> float:
    """
    Mètrica 4 — Profunditat relativa del camí òptim.
 
    Volem recompensar puzzles on la solució és llarga *en relació* a l'espai
    total. Intuïció: si cal recórrer molts passos per un laberint dens, el
    puzzle és més interessant que un camí llarg en un espai buit.
 
    Fórmula: log2(1 + longitud) / log2(1 + num_estats)
      - Si longitud ≈ num_estats (camí que omple tot l'espai) → score ≈ 1.0
      - Si longitud << num_estats (camí curt en espai vast) → score petit
      - Ambdós valors a 0 → 0.0 per convenció
      - Creixement logarítmic evita que un sol estat de diferència domini.
 
    Nota: el codi original usava `1 - longitud/num_estats`, que penalitzava
    exactament els puzzles més difícils (camí llarg = ratio gran = score baix).
    """
    if num_estats <= 0 or longitud_optima <= 0:
        return 0.0
    return math.log2(1 + longitud_optima) / math.log2(1 + num_estats)
 
 
def score_ponts(g: gt.Graph) -> float:
    """
    Mètrica 5 — Ponts estructurals al graf no dirigit subjacent.
 
    Un pont és una aresta la eliminació de la qual desconnecta el graf; indica
    que el puzzle té "fases" obligatòries (colls d'ampolla). Més ponts → puzzle
    més segmentat i, en general, més difícil de resoldre.
 
    Usem GraphView (vista sense còpia) per eficiència.
    """
    g_no_dir = gt.GraphView(g, directed=False)
    _, arestes_pont, _ = gt.label_biconnected_components(g_no_dir)
    num_ponts = int(arestes_pont.a.sum())
    return _normalitzar(num_ponts, PONTS_MAX_REF)
 
 
# ---------------------------------------------------------------------------
# Funció principal d'avaluació
# ---------------------------------------------------------------------------
 
def avaluar_puzzle(pz: Puzzle) -> dict:
    """
    Avalua un puzzle en dues passades independents:
 
      1. Graf complet (sense límit artificial): extreu num_estats, num_solucions
         i ponts estructurals. Per puzzles molt grans les mètriques d'espai i
         ponts saturen ràpid a 1.0, que és el comportament correcte (un puzzle
         amb 100k estats és, per definició, d'espai màxim).
 
      2. A* exacte: obté la longitud òptima sense dependre de la mida del graf.
 
    Retorna un diccionari amb les puntuacions parcials i la final (0.0-5.0).
    """
    # --- Passada 1: graf estructural (sense límit) ---------------------------
    # No posem limit_estats perquè:
    #   a) La mètrica d'espai és lineal saturada: puzzles molt grans reben 1.0
    #      tant si explorem 35k estats com 350k.
    #   b) La mètrica de ponts es fa sobre el graf real; un graf truncat donaria
    #      una topologia falsa (ponts artificials als fronts de tall).
    #   c) Per als mides de taulell que generem (4-7 x 4-7), l'espai d'estats
    #      rarament supera els 200k, perfectament manejable en memòria.
    g, nodes_desti = generar_graf(pz)
 
    num_estats    = g.num_vertices()
    num_solucions = len(nodes_desti)
 
    # --- Passada 2: resolució exacta amb A* ---------------------------------
    cami_optim = _a_star_real(pz)
 
    if cami_optim is None:
        return {
            "resoluble":       False,
            "num_estats":      num_estats,
            "num_solucions":   num_solucions,
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
 
    longitud_optima = len(cami_optim)
 
    # --- Mètriques ----------------------------------------------------------
    s_longitud   = score_longitud(longitud_optima)
    s_espai      = score_espai(num_estats)
    s_unicitat   = score_unicitat(num_solucions)
    s_eficiencia = score_eficiencia(longitud_optima, num_estats)
    s_ponts      = score_ponts(g)
 
    puntuacio_norm = (
        PES_LONGITUD_SOLUCIO * s_longitud  +
        PES_ESPAI_ESTATS     * s_espai     +
        PES_UNICITAT_SOLUCIO * s_unicitat  +
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
 
 
# ---------------------------------------------------------------------------
# Impressió del resultat
# ---------------------------------------------------------------------------
 
def imprimir_avaluacio(pz: Puzzle, resultat: dict) -> None:
    """Imprimeix per pantalla un resum llegible de l'avaluació."""
    print(f"Taulell:          {pz.W}x{pz.H}  ({len(pz.pieces)} peces)")
    print(f"Resoluble:        {'Sí' if resultat['resoluble'] else 'No'}")
    print(f"Estats totals:    {resultat['num_estats']}")
    print(f"Solucions (dest): {resultat['num_solucions']}")
    print(f"Longitud òptima:  {resultat['longitud_optima']} moviments")
    print()
    print("Mètriques parcials (0-1):")
    for nom, val in resultat["scores"].items():
        barra = "█" * int(val * 20)
        print(f"  {nom:<12} {val:.3f}  {barra}")
    print()
    print(f"Puntuació final:  {resultat['puntuacio']:.2f} / 5.00  {'⭐' * round(resultat['puntuacio'])}")
 
 
# ---------------------------------------------------------------------------
# Punt d'entrada
# ---------------------------------------------------------------------------
 
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Ús: python3 {sys.argv[0]} <puzzle.json>")
        sys.exit(1)
 
    puzzle_path = Path(sys.argv[1])
    pz = Puzzle.from_json(puzzle_path.read_text())
 
    resultat = avaluar_puzzle(pz)
    imprimir_avaluacio(pz, resultat)
 