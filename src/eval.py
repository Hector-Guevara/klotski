"""
Avalua un puzzle de peces lliscants mesurant l'interès del seu graf d'estats.

La puntuació final (de 0.0 a 5.0) combina diverses mètriques del graf:
  - Longitud de la solució òptima (puzzles més llargs → més interessants)
  - Nombre total d'estats accessibles (espai de cerca gran → més complex)
  - Nombre d'estats finals (menys solucions → més difícil)
  - Proporció d'estats que formen part del camí òptim (eficiència del camí)
  - Centralitat de pont: si hi ha colls d'ampolla al graf (fases del puzzle)

Ús: python3 eval.py <puzzle.json>
"""

from __future__ import annotations

import sys
import json
import math
from pathlib import Path

import graph_tool.all as gt  # type: ignore[import-untyped]

from graph import generar_graf
from puzzle import Puzzle
from solve import _a_star_real


# ---------------------------------------------------------------------------
# Pesos de cada mètrica en la puntuació final (han de sumar 1.0)
# ---------------------------------------------------------------------------

PES_LONGITUD_SOLUCIO  = 0.35  
PES_ESPAI_ESTATS      = 0.25  
PES_UNICITAT_SOLUCIO  = 0.20  
PES_EFICIENCIA_CAMI   = 0.10  
PES_PONTS             = 0.10  


# ---------------------------------------------------------------------------
# Llindars de referència calibrats
# ---------------------------------------------------------------------------

LONGITUD_MAX_REF  = 90    # Moviments (ajustat per puzzles top)
ESTATS_MAX_REF    = 35000 # Nodes (ajustat per puzzles top)
PONTS_MAX_REF     = 20    # Colls d'ampolla estructurals


def normalitzar(valor: float, maxim: float) -> float:
    """Normalitza un valor positiu a [0, 1] fent servir una saturació lineal."""
    return min(valor / maxim, 1.0)


def score_longitud(longitud_optima: int) -> float:
    """Mètrica 1 — Longitud de la solució òptima."""
    return normalitzar(longitud_optima, LONGITUD_MAX_REF)


def score_espai(num_estats: int) -> float:
    """Mètrica 2 — Mida de l'espai d'estats accessibles."""
    return normalitzar(num_estats, ESTATS_MAX_REF)


def score_unicitat(num_solucions: int) -> float:
    """Mètrica 3 — Unicitat de la solució."""
    if num_solucions == 0:
        return 0.0
    # SOLUCIÓ BUG: Utilitzem log2 perquè 1 solució = 1.0 de nota (1 / log2(2) = 1)
    return 1.0 / math.log2(1 + num_solucions)


def score_eficiencia(longitud_optima: int, num_estats: int) -> float:
    """Mètrica 4 — Eficiència del camí òptim."""
    if num_estats == 0:
        return 0.0
    ratio = longitud_optima / num_estats
    return max(0.0, 1.0 - ratio)


def score_ponts(g: gt.Graph) -> float:
    """Mètrica 5 — Presència de ponts al graf no dirigit subjacent."""
    # OPTIMITZACIÓ: GraphView evita copiar el graf en memòria, molt més ràpid!
    g_no_dir = gt.GraphView(g, directed=False)
    comp, arestes_pont, _ = gt.label_biconnected_components(g_no_dir)
    num_ponts = int(arestes_pont.a.sum())
    return normalitzar(num_ponts, PONTS_MAX_REF)


# ---------------------------------------------------------------------------
# Funció principal d'avaluació
# ---------------------------------------------------------------------------

def avaluar_puzzle(pz: Puzzle) -> dict:
    """
    Donat un puzzle, en genera el graf i calcula totes les mètriques.
    Retorna un diccionari amb les puntuacions parcials i la final (0.0-5.0).
    """
    # 1. Generem el graf, però limitem la cerca a 40.000 estats per no col·lapsar.
    # Si un puzzle passa d'aquí, ja rebrà el 5.0 en la mètrica d'espai igualment.
    g, nodes_desti = generar_graf(pz, limit_estats=40000)

    num_estats    = g.num_vertices()
    num_solucions = len(nodes_desti)

    # 2. Resolem el puzzle amb l'A* real (calcula el camí exacte i més ràpid)
    cami_optim = _a_star_real(pz)

    # Si l'A* no troba camí, el puzzle no és resoluble
    if cami_optim is None:
        return {
            "resoluble":        False,
            "num_estats":       num_estats,
            "num_solucions":    0,
            "longitud_optima":  0,
            "scores": {
                "longitud":   0.0,
                "espai":      0.0,
                "unicitat":   0.0,
                "eficiencia": 0.0,
                "ponts":      0.0,
            },
            "puntuacio": 0.0,
        }

    longitud_optima = len(cami_optim)

    # PARCHE: Si el graf s'ha tallat a 40.000 estats abans d'arribar a la meta, 
    # num_solucions seria 0. Com que l'A* SÍ ha trobat solució, garantim que sigui 1.
    if num_solucions == 0:
        num_solucions = 1

    # Calculem totes les mètriques parcials
    s_longitud   = score_longitud(longitud_optima)
    s_espai      = score_espai(num_estats)
    s_unicitat   = score_unicitat(num_solucions)
    s_eficiencia = score_eficiencia(longitud_optima, num_estats)
    s_ponts      = score_ponts(g)

    # Puntuació ponderada final, escalada a [0, 5]
    puntuacio_norm = (
        PES_LONGITUD_SOLUCIO  * s_longitud  +
        PES_ESPAI_ESTATS      * s_espai     +
        PES_UNICITAT_SOLUCIO  * s_unicitat  +
        PES_EFICIENCIA_CAMI   * s_eficiencia +
        PES_PONTS             * s_ponts
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
        "puntuacio":       puntuacio,
    }


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