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
from pathlib import Path

import graph_tool.all as gt  # type: ignore[import-untyped]

from graph import generar_graf
from puzzle import Puzzle
from math import log 
from solve import _a_star_real


# ---------------------------------------------------------------------------
# Pesos de cada mètrica en la puntuació final (han de sumar 1.0)
# ---------------------------------------------------------------------------

PES_LONGITUD_SOLUCIO  = 0.35  # la mètrica més rellevant per a la dificultat
PES_ESPAI_ESTATS      = 0.25  # recompensa puzzles amb molt espai de cerca
PES_UNICITAT_SOLUCIO  = 0.20  # penalitza puzzles amb moltes solucions trivials
PES_EFICIENCIA_CAMI   = 0.10  # recompensa que el camí òptim no sigui obvi
PES_PONTS             = 0.10  # recompensa l'existència de fases (ponts al graf)


# ---------------------------------------------------------------------------
# Llindars de referència per normalitzar cada mètrica a [0, 1]
# Ajustats empíricament observant puzzles de mostra.
# ---------------------------------------------------------------------------

LONGITUD_MAX_REF  = 30   # moviments; puzzles de més de 80 es consideren 'perfectes'
                         # referència: simplicity=31, 2swap=17, klotski=116
ESTATS_MAX_REF    = 2000 # nodes; referència: klotski i 2swap (2 caselles lliures)
                         # generen grafs molt densos; 8000 és un llindar realista
PONTS_MAX_REF     = 10   # número de ponts; més de 10 → puntuació màxima


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
    return 1.0 / log(1 + num_solucions)


def score_eficiencia(longitud_optima: int, num_estats: int) -> float:
    """Mètrica 4 — Eficiència del camí òptim."""
    if num_estats == 0:
        return 0.0
    ratio = longitud_optima / num_estats
    return max(0.0, 1.0 - ratio)


def score_ponts(g: gt.Graph) -> float:
    """Mètrica 5 — Presència de ponts al graf no dirigit subjacent."""
    g_no_dir = gt.Graph(g, directed=False)
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
    # El graf se sigue generando porque aporta las métricas de tamaño, soluciones y puentes
    g, nodes_desti = generar_graf(pz)

    num_estats    = g.num_vertices()
    num_solucions = len(nodes_desti)

    # llamamos directamente a tu algoritmo A* híbrido ultra rápido y preciso.
    cami_optim = _a_star_real(pz)

    # Si el A* no encuentra camino, el puzzle no es resoluble
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

    # Es calculen totes les mètriques parcials amb la longitud exacta
    s_longitud  = score_longitud(longitud_optima)
    s_espai     = score_espai(num_estats)
    s_unicitat  = score_unicitat(num_solucions)
    s_eficiencia = score_eficiencia(longitud_optima, num_estats)
    s_ponts     = score_ponts(g)

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
        "puntuacio": puntuacio,
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