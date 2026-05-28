 Klotski! (Pràctica 2 d'AP2, Primavera de 2026)

# Visió Global del Projecte

## Què és Klotski?

El **Klotski** és un trencaclosques clàssic de peces lliscants: un conjunt de peces de formes i mides diverses col·locades sobre un taulell rectangular, on l'objectiu és moure una peça concreta fins a una posició determinada, desplaçant les altres per fer-li camí. Les peces només es poden moure en una de les quatre direccions (N, S, E, W) i no poden solapar-se ni sortir del taulell.

El que fa interessant aquest joc des d'un punt de vista de programació és que el nombre de posicions possibles pot créixer molt ràpidament amb el nombre de peces i la mida del taulell — el Klotski original necessita **116 moviments** per resoldre's i té desenes de milers de posicions possibles. Això significa que un humà que ho intenti "a cegues" pot trigar hores, mentre que un algorisme ben fet ho resol en fraccions de segon.

La versió que implementem aquí és més general que el joc comercial: les peces poden tenir qualsevol forma fins a mida 4 (no només rectangles), el taulell pot ser de qualsevol mida, i es poden afegir parets (caselles bloquejades). Això ens permet crear puzzles originals que no existeixen en cap joc comercial.

## Objectiu del Projecte

L'objectiu d'aquesta pràctica és construir un **sistema complet** que permeti:

1. **Generar** puzzles de Klotski de forma automàtica en tres nivells de dificultat (`easy`, `medium`, `hard`), garantint que es puguin resoldre i avaluant-los per retornar sempre el millor.
2. **Avaluar** la qualitat i dificultat de cada puzzle amb cinc mesures basades en l'estructura del joc, combinades en una nota final de 0 a 5 estrelles.
3. **Resoldre** qualsevol puzzle de forma òptima (el menor nombre de moviments possible) amb un algorisme A*, sense necessitat de construir el graf complet.
4. **Visualitzar** el taulell i la solució, tant de forma interactiva (PyGame) com en GIF animat o en un graf 3D interactiu al navegador.
5. **Interactuar** amb un repositori compartit per descarregar, puntuar i pujar puzzles, contribuint a un rànquing col·lectiu.

El resultat és un sistema complet: des de la generació fins a la publicació, passant per la resolució i la visualització. Cada part s'ha dissenyat per ser independent, de manera que combinar-les és senzill.

***

## Principals Dificultats

### Garantir que el puzzle es pugui resoldre

Un puzzle generat a l'atzar té moltes probabilitats de ser **irresoluble**: les peces poden quedar encallades sense cap manera d'arribar a l'objectiu. El generador actual col·loca les peces una a una fins a arribar a la densitat d'ocupació que toca per al nivell, i després comprova si el puzzle es pot resoldre. Els que no es poden resoldre es descarten i es torna a intentar, de manera que el sistema sempre retorna un puzzle vàlid.

### Ordre fix de les peces

La classe `Puzzle` exigeix que les peces estiguin en un **ordre concret** — ordenades de menor a major per forma i posició inicial. Això és necessari per a la consistència: dos puzzles iguals han de tenir el mateix JSON i el mateix identificador. Sense això, el repositori podria acumular duplicats i comparar puzzles seria impossible.

Però aquest ordre complica la generació: cada cop que s'afegeix una peça, cal reordenar totes les peces i les seves posicions, ja que l'índex de cada peça determina la seva posició dins de la llista `start`. Si s'afegeix una peça "petita" que hauria d'anar primer, tots els índexos canvien i cal actualitzar-ho tot.

### Massa posicions possibles

Per a puzzles amb moltes peces, el nombre de posicions possibles pot superar els centenars de milers. Construir el graf complet per a cada puzzle durant la generació seria inassumible: amb 150 intents per al nivell `hard`, es podrien estar construint grafs enormes repetidament, cosa que faria el sistema molt lent.

El sistema resol aquest problema de dues maneres: la clau canònica redueix l'espai de cerca de l'A* en un factor gran quan hi ha peces repetides, i `eval.py` limita l'exploració del graf a 200.000 posicions per intent, usant l'A* com a alternativa quan no arriba a la solució dins del límit.

### Mesurar la dificultat de manera objectiva

Definir "dificultat" de forma objectiva és complicat. Un puzzle amb solució de 50 moviments pot ser senzill si tots els moviments són obvis; un de 20 moviments pot ser molt difícil si requereix una seqüència molt concreta. Per capturar aquesta riquesa, hem optat per una **nota basada en cinc mesures** del graf de posicions, cadascuna capturant un aspecte diferent: longitud de la solució, nombre de posicions possibles, nombre de camins fins a la meta, profunditat del camí òptim respecte al total, i existència de "colls d'ampolla" on hi ha un moviment obligatori.

***

## Estructura del Sistema i Comandes

El projecte s'organitza en mòduls independents. A continuació es mostra el flux típic d'ús i les comandes corresponents. Aquesta part és útil per a qualsevol persona que vulgui provar el codi, ja que per molt bo que sigui, sense saber les comandes no es pot fer res. Tot i que cada fitxer té les instruccions al seu docstring inicial, creiem important tenir-ho tot recollit en un sol lloc.

### Inicialització de l'entorn

```bash
pixi shell
# Per inicialitzar el pixi, no funcionarà si no comencem per aquesta comanda.
# Cal tenir el pixi i totes les dependències especificades a l'enunciat instal·lades.
```

### Generació d'un puzzle

```bash
python3 src/generate.py <easy|medium|hard> [wall] [multigoal] <nom_puzzle>
```

Exemples:
```bash
python3 src/generate.py hard puzzles/puzzle_dificil
python3 src/generate.py hard wall multigoal puzzles/puzzle_dificil_parets
# Resultat: puzzles/puzzle_dificil.json
```

### Resolució

```bash
python3 src/solve.py <puzzle.json>
# Resultat: puzzle.sol.json
```

### Avaluació de qualitat

```bash
python3 src/eval.py <puzzle.json>
```

### Visualització estàtica (PNG)

```bash
python3 src/image.py <puzzle.json>
```

### Joc interactiu

```bash
python3 src/play.py <puzzle.json>
```

### Animació GIF de la solució

```bash
python3 src/movie.py <puzzle.json> <puzzle.sol.json> [output.gif]
```

### Generació i visualització del graf 3D

```bash
python3 src/graph.py <puzzle.json>
python3 src/3D_view.py <puzzle.graphml> [puzzle.sol.json]
```

### Interacció amb el repositori compartit

```bash
# Descarregar tots els puzzles
python3 src/download.py

# Descarregar un puzzle específic per ID
python3 src/download.py <puzzle_id>

# Pujar un puzzle
python3 src/upload.py <puzzle.json> <token>

# Avaluar i puntuar un puzzle del repositori
python3 src/rate.py <puzzle_id> <token>

# Puntuar tots els puzzles del repositori
python3 src/rate_all.py <token> [--skip-errors]
```

***

# Descripció Detallada dels Mòduls

Aquesta secció explica els algorismes que hem fet servir, per què hem pres certes decisions i com estan organitzats els fitxers. No cal llegir-la per poder usar el sistema, però ajuda a entendre com funciona per dins i pot servir d'inspiració per a altres implementacions.

## Representació de Dades: `puzzle.py`

### Què fa

Defineix els tres tipus bàsics del sistema:

- **`Piece`**: la forma d'una peça com una llista de coordenades relatives normalitzades. La normalització vol dir que `min(x) == 0` i `min(y) == 0`, és a dir, la peça sempre es representa com si estigués a la cantonada superior esquerra, independentment d'on estigui al taulell.
- **`State`**: la posició de totes les peces en un moment donat — simplement una llista de posicions, una per peça, en el mateix ordre que les peces del puzzle. Separar `Puzzle` (forma + objectiu) de `State` (posicions) permet reutilitzar la definició del puzzle per a molts estats sense duplicar res.
- **`Puzzle`**: el trencaclosques complet: mides `W × H`, parets, peces, estat inicial i llista d'objectius `(índex_peça, posició_meta)`. Inclou mètodes per convertir-lo a JSON i calcular un identificador únic SHA-256.

### Decisions de disseny destacades

**Tot és immutable** (`frozen=True`): les tres classes no es poden modificar un cop creades i es poden usar com a claus de diccionari directament. Això és molt important per a l'A* i el generador de grafs, que necessiten una taula de "ja he estat aquí" eficient. Un `State` pot ser clau d'un diccionari sense cap conversió extra.

**Validació a `__post_init__`**: quan es crea un `Puzzle`, es comprova automàticament que les peces no se solapen, que estan en l'ordre correcte, que les parets estan dins del taulell i que els índexos d'objectiu són vàlids. Si algun d'aquests requisits falla, es llança un error immediatament. Això fa que qualsevol `Puzzle` que existeixi al sistema sigui sempre consistent.

**Ordre fix de peces**: les peces s'ordenen per `(forma, posició_inicial)`. Això garanteix que dos puzzles amb les mateixes peces en les mateixes posicions, però creats en ordre diferent, produeixin el mateix JSON i el mateix identificador. Sense això, el repositori podria acumular duplicats.

**`Piece.normalized`**: mètode que normalitza coordenades qualsevol en una `Piece` vàlida. Permet al generador treballar amb coordenades absolutes i normalitzar al final, sense haver de gestionar manualment el desplaçament mínim.

***

## Lògica del Joc: `logic.py`

### Què fa

Implementa tota la mecànica del joc: comprovar si un moviment és vàlid, aplicar-lo, calcular fins on pot lliscar una peça, llistar tots els moviments possibles des d'una posició i comprovar si s'ha assolit l'objectiu.

### Decisions de disseny destacades

**`can_move` separat de `apply_move`**: tenir una funció per comprovar i una altra per aplicar permet al codi que la crida (A*, generador de grafs) consultar si un moviment és possible sense crear posicions intermèdies. Això és especialment útil a `max_slide`, que calcula fins on pot arribar una peça cridant `can_move` repetidament fins que troba un bloqueig, i a `play.py`, que necessita saber el rang de lliscament per limitar l'arrossegament del ratolí.

**Moviments d'un sol pas**: `possible_moves` retorna moviments de distància 1. Aquesta granularitat és la correcta per construir el graf de posicions: cada connexió correspon a exactament un moviment elemental, cosa que garanteix que la distància al graf és exactament el nombre de moviments. `apply_move` accepta distàncies majors per permetre lliscaments sencers des del joc interactiu, amb validació pas a pas.

**`replay_moves`**: permet reproduir una seqüència de moviments des de la posició inicial i obtenir totes les posicions intermèdies. `movie.py` el fa servir per animar la solució fotograma a fotograma; `3D_view.py` el fa servir per identificar les connexions del camí òptim al graf i ressaltar-les en groc.

***

## Generació de Puzzles: `generate.py`

### Què fa

Genera puzzles nous en format `.json` a partir d'un nivell de dificultat (`easy`, `medium`, `hard`), amb opcions addicionals per activar parets (`wall`) i múltiples objectius (`multigoal`). La interfície és:

```bash
python src/generate.py hard puzzles/el_meu_puzzle
python src/generate.py hard wall multigoal puzzles/el_meu_puzzle_complex
```

El programa tria automàticament les mides del taulell, la densitat d'ocupació, les formes de les peces i la posició objectiu en funció del nivell, sense que l'usuari hagi d'especificar res més. Tots els puzzles es desen automàticament a la carpeta `puzzles/`.

### El catàleg de formes i els pesos per nivell

El sistema inclou **28 formes** de poliominós fins a mida 4 (peces d'1, 2, 3 i 4 caselles en totes les orientacions). Cada nivell té unes mides de taulell fixes i uns pesos que controlen quines mides de peça surten més:

| Nivell | Dimensions | Mides preferides | Densitat | Parets |
|--------|------------|-----------------|----------|--------|
| easy   | 4×4, 4×5   | Petites (mida 1–2) | 65%   | Opcional     |
| medium | 5×5        | Mitjanes (mida 1–3) | 75%  | Opcional     |
| hard   | 5×6, 6×5   | Mixtes (mida 1–4)  | 86%  | Opcional |

Les peces grans restringeixen més el taulell i generen puzzles amb menys camins alternatius. Un taulell al 86% d'ocupació deixa tan poc espai de maniobra que les peces queden gairebé encaixades entre si, obligant a seqüències de moviments llargues per desencallar la peça objectiu.

Per al nivell `hard` amb parets activades, el generador augmenta la probabilitat de triar peces petites (1×1) per assegurar que hi hagi prou peces petites als voltants dels obstacles que permetin moure les peces grans. Sense aquest ajust, la combinació de moltes peces grans i parets centrals generava taulells completament bloquejats d'entrada on cap peça podia moure's.

### Generació directa amb densitat obligatòria

El generador col·loca peces aleatòries una a una fins a arribar a la densitat objectiu del nivell, i descarta el puzzle si no l'assoleix (la diferència entre l'àrea ocupada i `area_max` ha de ser com a màxim 1). Això garanteix que tots els puzzles acceptats tinguin una densitat uniforme, cosa important per a la consistència de les notes d'avaluació.

La primera peça col·locada sempre és un tetròmino (mida 4) triat a l'atzar, per assegurar que el taulell tingui almenys una peça gran que actuï com a obstacle principal. Les peces següents es trien seguint els pesos del nivell, amb un sistema de fallback progressiu: si una peça gran no hi cap en cap posició lliure, es prova un dòmino; si tampoc, una peça 1×1. Això evita que el generador es quedi encallat sense poder col·locar cap peça.

La posició objectiu es tria entre les posicions més llunyanes en distància de la posició inicial de la peça (distància mínima de 3 caselles per evitar solucions trivials) que no se solapen amb les parets. La peça objectiu és sempre la més gran del taulell — les peces grans tenen menys posicions possibles, cosa que redueix el nombre de solucions al graf i augmenta la nota de la mesura d'unicitat.

Comparat amb un enfocament que parteix de la solució i "desfà" moviments cap enrere, aquest mètode és més senzill però requereix comprovar la resolubilitat després. La compensació és acceptable: cada intent individual és molt més ràpid, i la comprovació la fa `eval.py` igualment per calcular les mesures.

### Selecció del millor puzzle entre múltiples intents

El sistema fa fins a `max_intents` intents (50 per a `easy`, 100 per a `medium`, 150 per a `hard`) i avalua cada puzzle resoluble amb `eval.py`. Es guarda el millor (nota més alta) i s'atura quan s'assoleix la nota mínima del nivell (1.0, 2.0 i 3.6 respectivament). Si cap intent arriba a la nota mínima, es retorna el millor trobat amb un avís — el programa mai falla per no trobar res prou bo.

En temps real es mostra cada intent, de manera que l'usuari pot veure com progressa la cerca, per exemple:

```
  →  Intent   3/150: Generant...  Avaluant... ✅ RESOLUBLE! (4231 estats) — Nota: 3.12
  →  Intent   7/150: Generant...  Avaluant... ✅ RESOLUBLE! (8901 estats) — Nota: 3.71
  ✓ Puntuació objectiu assolida a l'intent 7.
```

***

## Resolució Òptima: `solve.py`

### Què fa i per què no usa el graf

Resol qualsevol puzzle de forma **òptima** (el menor nombre de moviments possible) i genera un fitxer `.sol.json` amb la seqüència de moviments.

L'enunciat planteja resoldre el puzzle a partir del graf generat per `graph.py`, fent un `shortest_path` sobre ell. Aquesta és una aproximació teòricament correcta, però té un problema molt gran en la pràctica: **construir el graf complet és el punt més lent de tot el sistema**. Per a un puzzle de nivell `hard` amb 50.000–100.000 posicions possibles, construir el graf pot trigar entre 30 i 90 segons. Si `solve.py` depengués del graf, cada cop que es vol resoldre un puzzle caldria esperar tot aquest temps, cosa que fa el sistema completament inutilitzable.

La solució és usar un **A\*** directament sobre les posicions reals, sense construir el graf. L'A* és un algorisme de cerca que explora les posicions per ordre de `f(n) = g(n) + h(n)`, on `g(n)` és el nombre de moviments fets fins ara i `h(n)` és una estimació del que queda fins a la solució. La seva clau és que no necessita explorar totes les posicions per trobar el camí òptim — es guia per l'estimació i mira primer les posicions que semblen més prometedores.

L'estimació triada és la **distància de Manhattan** de la peça objectiu fins a la seva posició meta:

```
h(estat) = |x_actual - x_meta| + |y_actual - y_meta|
```

Aquesta estimació mai sobreestima el cost real, perquè en el millor cas imaginable — sense cap obstacle, en línia recta — la peça objectiu trigaria exactament tants moviments com la seva distància de Manhattan. La realitat sempre és igual o pitjor (hi ha peces que bloquegen el camí). Amb una estimació que mai sobreestima, l'A* garanteix sempre la solució **òptima** — mai una seqüència de moviments més llarga del mínim necessari. Aquesta propietat és exactament equivalent a la que oferiria el `shortest_path` sobre el graf, però sense el cost de construir-lo.

En la pràctica, per a puzzles `medium` típics, l'A* troba la solució òptima explorant menys d'un 10% de les posicions que exploraria una cerca exhaustiva. Per a puzzles `hard` la millora és encara més gran.

### La clau que redueix l'espai de cerca

La part més important per a l'eficiència és com es gestionen les posicions ja visitades. Si usem `State` directament com a clau, dues posicions que difereixen únicament en quina de les peces 1×1 iguals ocupa cada casella es tractarien com a posicions **diferents**, duplicant inútilment la feina.

La solució és una **clau que agrupa peces iguals** (`canonical_key`):

- Les **peces objectiu** es guarden per identitat exacta. La seva posició individual importa perquè l'objectiu depèn d'on és concretament.
- Les **peces no-objectiu iguals** s'agrupen per forma i les seves posicions s'ordenen. No importa *quina* peça 1×1 ha mogut — importa *on estan* les peces d'aquella forma.

Per exemple, en un puzzle amb cinc peces 1×1 no-objectiu, en lloc de tractar les $5! = 120$ ordenacions com a posicions diferents, la clau les tracta totes com una sola. Això pot reduir l'espai de cerca en un factor molt gran quan hi ha moltes peces iguals, cosa que marca la diferència entre una cerca de minuts i una de mil·lisegons. La mateixa clau s'usa a `graph.py`, cosa que garanteix que el graf i l'A* treballen sobre el **mateix espai de posicions**.

### Format de la solució

```json
[[2, "W", 1], [0, "N", 1], [3, "E", 1], ...]
```

Cada element és `[índex_peça, direcció, distància]`. La distància és sempre 1, cosa que garanteix la compatibilitat directa amb `movie.py` i `3D_view.py`.

***

## Generació del Graf de Posicions: `graph.py`

### Què fa i quan s'usa

Explora totes les posicions accessibles des de l'estat inicial i construeix el **graf dirigit complet** amb `graph-tool`, una biblioteca molt ràpida escrita en C++ amb accés des de Python. Cada node és una posició possible del taulell; cada connexió és un moviment elemental entre dues posicions.

El graf té dos usos ben diferenciats: per a la **visualització 3D** (on es vol el graf complet per veure tota l'estructura), i per a **`eval.py`** (on es genera amb límit de posicions per a les mesures). Per a la resolució, com s'ha explicat a `solve.py`, el graf no és necessari — l'A* el substitueix amb avantatge.

### Construcció ràpida en bloc

La diferència de velocitat entre construir un graf element per element i fer-ho tot d'un cop és d'**1 a 2 ordres de magnitud**. Cada crida de Python a C++ té un cost fix que per a milers d'operacions s'acumula molt.

El procés elimina aquest cost en tres fases:

1. **Exploració pura en Python**: es fa una cerca des de la posició inicial, acumulant totes les connexions en una llista Python i les dades de cada node en arrays. Cap crida a `graph-tool` durant aquesta fase.
2. **Construcció en bloc**: una sola crida a `g.add_vertex(n)` crea tots els nodes alhora, i una sola crida a `g.add_edge_list(edges)` crea totes les connexions amb codi C++ vectoritzat.
3. **Assignació de propietats en bloc**: les propietats booleanes s'assignen com a arrays directament, sense iterar sobre els nodes un per un.

Per a un graf de 5.000 nodes i 30.000 connexions, la construcció tarda menys d'un segon, mentre que la construcció pas a pas podria trigar 10–30 segons.

### El límit de posicions

`generar_graf` accepta un paràmetre opcional `limit_estats`. Quan s'activa (com fa `eval.py`), l'exploració s'atura quan s'arriba al límit. Per a puzzles que el superen, les mesures d'espai i ponts saturen al màxim per disseny (el comportament correcte: un puzzle amb >200.000 posicions és màxim en espai), i la longitud òptima es calcula per l'A* com a alternativa.

***

## Avaluació de Qualitat: `eval.py`

### Què fa

Assigna una **nota de 0.0 a 5.0** a un puzzle combinant cinc mesures del seu graf de posicions. Qualsevol puzzle pot ser avaluat en pocs segons, cosa que permet filtrar-los durant la generació sense bloquejar el sistema.

### Arquitectura en dues passades amb alternativa intel·ligent

| Passada | Eina | Mesures obtingudes |
|---------|------|---------------------|
| 1 | `generar_graf(limit_estats=200_000)` | `num_estats`, `num_solucions`, ponts |
| 2 | `shortest_distance` (C++) o A* (alternativa) | `longitud_optima` |

El límit de 200.000 posicions és un equilibri entre velocitat i precisió: prou gran per no tallar la majoria de puzzles `easy` i `medium` (que rarament superen les 50.000 posicions), però amb un sostre que evita esperes de minuts per a puzzles `hard` molt densos.

El sistema és **adaptatiu**: si la posició objectiu és assolible dins del límit, la longitud òptima s'obté amb `gt.shortest_distance` en C++ pur — una sola passada sobre el graf ja construït, gairebé instantània. Si el graf s'ha tallat abans d'arribar a la solució, es fa servir `_a_star_real` com a alternativa. Tot i ser Python, l'A* és ràpid gràcies a l'estimació de Manhattan: no cal explorar tot l'espai, sinó només les posicions que s'acosten a la meta. En aquest cas, `num_estats` es força al valor del límit com a mínim, per tal que la mesura d'espai reflecteixi que el puzzle és gran.

### Les cinc mesures

**Mesura 1 — Longitud de la solució òptima** (pes 0.35):
La mesura més important. Normalitzada linealment fins a `LONGITUD_MAX_REF = 90` moviments — el Klotski original té ~116, però per als taulells que generem (fins a 6×7), 90 és el màxim realista.

**Mesura 2 — Nombre de posicions possibles** (pes 0.25):
Moltes posicions possibles significa que el jugador es pot "perdre" fàcilment. Normalitzada fins a `ESTATS_MAX_REF = 200.000`. Puzzles que superen el límit d'exploració reben la nota màxima en aquesta mesura.

**Mesura 3 — Unicitat de la solució** (pes 0.20):
Menys camins que porten a la meta significa que el jugador ha de trobar un camí molt concret. Usa `1 / log₂(1 + n)`, que dóna exactament 1.0 per a 1 solució i baixa suaument: 2 solucions → 0.63, 10 → 0.29, 100 → 0.15. La base 2 és l'única que garanteix `f(1) = 1.0` sense cap factor addicional — amb base $e$, `1 / ln(2) ≈ 1.44 > 1`, que sortiria del rang `[0, 1]`.

**Mesura 4 — Profunditat relativa del camí** (pes 0.10):
`log₂(1 + longitud) / log₂(1 + num_estats)`. Recompensa puzzles on el camí òptim és llarg *en relació* al nombre total de posicions: cal explorar molt per trobar la solució. La versió anterior d'aquesta mesura (`1 - longitud/num_estats`) penalitzava per error els puzzles amb solució llarga en espais grans, exactament els més interessants.

**Mesura 5 — Colls d'ampolla** (pes 0.10):
Un "coll d'ampolla" al graf és una connexió que, si s'elimina, fa que el graf quedi separat en dues parts — indica que hi ha un moviment concret que és **obligatori** per resoldre el puzzle. Puzzles amb molts d'aquests punts obligatoris tenen "fases" ben diferenciades. Es detecten amb `label_biconnected_components` sobre una vista no dirigida del graf, que evita còpies en memòria.

### Nota final

$$\text{nota} = 5.0 \times \left( 0.35 \cdot s_\text{long} + 0.25 \cdot s_\text{esp} + 0.20 \cdot s_\text{uni} + 0.10 \cdot s_\text{ef} + 0.10 \cdot s_\text{ponts} \right)$$

Els pesos sumen exactament 1.0. El factor 5.0 escala el resultat a l'interval `[0, 5]`, compatible amb el sistema d'estrelles del repositori.

***

## Visualització Interactiva: `play.py`

### Què fa

Proporciona una interfície gràfica amb **PyGame** per jugar al puzzle manualment. L'usuari arrossega les peces amb el ratolí; el sistema detecta la direcció de moviment (horitzontal o vertical) un cop superat un llindar de píxels, i en alliberar el botó encaixa la peça a la casella més propera. La pantalla es torna groga quan el puzzle es resol.

### Decisions de disseny destacades

**Detecció de direcció** (`AXIS_THRESHOLD = 8px`): evita que un lleuger tremolor de la mà activi accidentalment el moviment en la direcció equivocada. La direcció només es fixa quan el desplaçament supera el llindar en un eix concret.

**Siluetes amb marge interior**: les peces no es dibuixen com a rectangles per casella, sinó com a **formes compactes** amb un petit marge interior (`PIECE_PAD = 3px`). Donada una peça en L de tres caselles, el sistema calcula el contorn de la unió de les tres caselles, simplifica els vèrtexs i aplica un marge cap a l'interior. El resultat és una peça visualment unida i clarament diferenciada de les veïnes.

**Visualització de l'objectiu en dues capes**: les caselles meta es dibuixen en dues passades — una per sota de les peces (zona gran, 45% de la casella) i una per sobre (punt petit, 15%). D'aquesta manera, l'objectiu sempre és visible independentment de quina peça el tapi.

***

## Animació: `movie.py`

### Què fa

Genera un GIF animat de la solució d'un puzzle, reproduint cada moviment com una animació fluida de la peça lliscant, amb una interpolació que suavitza l'inici i el final del moviment.

### Interpolació suavitzada

```python
def ease_in_out(t: float) -> float:
    if t < 0.5:
        return 4 * t**3
    return 1 - (-2*t + 2)**3 / 2
```

Aquesta funció fa que el moviment arranqui i freni suaument en lloc de moure's a velocitat constant. El resultat és molt més agradable visualment que un moviment lineal.

***

## Visualització del Graf 3D: `3D_view.py`

### Què fa

Carrega un fitxer `.graphml`, el converteix al format JSON de la biblioteca JavaScript **3d-force-graph** i obre una pàgina web interactiva al navegador. El navegador mostra el graf com una xarxa 3D on els nodes s'atreuen i es repel·leixen com si fossin partícules físiques fins a trobar un equilibri que mostra l'estructura del graf. Si s'afegeix un fitxer de solució, les connexions del camí òptim es ressalten en groc.

La visualització 3D és molt útil per entendre l'estructura dels puzzles: els grups de nodes molt connectats representen zones del taulell fàcils d'explorar; les connexions estretes entre grups representen els colls d'ampolla que fan el puzzle difícil. La solució òptima en groc mostra exactament per quins punts obligatoris cal passar.

El JSON del graf es manté en memòria i es serveix directament al navegador sense escriure cap fitxer temporal al disc, cosa que permet tancar el programa amb Ctrl+C sense deixar residus.

***

## Interacció amb el Repositori: `download.py`, `upload.py`, `rate.py`, `rate_all.py`

### Flux general

El repositori compartit `https://klotski.pauek.dev/api/puzzles` té una API senzilla:

| Mètode | Endpoint | Acció |
|--------|----------|-------|
| GET | `/api/puzzles` | Llista d'IDs dels 100 millors |
| GET | `/api/puzzles/<id>` | Descarrega un puzzle |
| POST | `/api/puzzles` | Puja un puzzle nou |
| POST | `/api/puzzles/<id>/votes` | Envia una valoració (1–5 estrelles) |

El servidor retorna els puzzles embolcallats en `{"puzzle": {...}, "stars": N}`. Totes les funcions de descàrrega extreuen automàticament la part del puzzle per desar-la en format estàndard local.

`download.py` gestiona tant la descàrrega individual (`download.py <id>`) com la massiva (`download.py` sense arguments), comprovant si el fitxer ja existeix per evitar descàrregues repetides.

`upload.py` valida el puzzle localment amb `Puzzle.from_json`, l'avalua amb `eval.py` i avisa si la nota és baixa (< 1.0), però permet enviar-lo igualment — la decisió final és de l'usuari.

`rate.py` automatitza la valoració d'un puzzle: el descarrega, el puntua amb `eval.py` (arrodonint a enter per compatibilitat amb l'API) i envia la valoració. `rate_all.py` aplica el mateix procés a tots els puzzles del repositori de forma seqüencial, amb gestió d'errors i l'opció `--skip-errors` per continuar malgrat fallades individuals. Executar `rate_all.py` periòdicament manté el rànquing del repositori actualitzat amb el nostre criteri d'avaluació.

***

# Conclusions

## Assoliments principals

El sistema construït és un pipeline complet que va des de la generació fins a la publicació col·laborativa de puzzles de Klotski. Les decisions més importants — la representació immutable amb ordre fix, la generació directa amb densitat obligatòria, la resolució per A* independent del graf, la clau que agrupa peces iguals, la construcció en bloc del graf i l'avaluació amb límit adaptatiu — responen cadascuna a un problema concret i es complementen entre si.

## Punts forts

- **Resolució independent del graf**: el solver A* no depèn de `graph.py`, eliminant el punt més lent de tot el sistema. Resoldre un puzzle `hard` típic tarda menys de 2 segons; amb el graf complet hauria tardat entre 30 i 90.
- **Eficiència a múltiples nivells**: la clau que agrupa peces iguals redueix l'espai de cerca de l'A* molt significativament quan hi ha peces repetides; la construcció en bloc del graf minimitza les crides de Python a C++; el límit adaptatiu d'`eval.py` permet avaluar puzzles en pocs segons durant la generació.
- **Modularitat real**: cada fitxer té una sola responsabilitat. `eval.py` no sap com s'ha generat el puzzle; `solve.py` no sap res del graf; `play.py` no depèn d'`eval.py`. Les dependències van sempre en la mateixa direcció: `generate` → `eval` → `graph` + `solve` → `logic` → `puzzle`.
- **Mesura de dificultat ben fonamentada**: les cinc mesures capturen aspectes diferents i independents de la dificultat, amb pesos calibrats a partir de proves i justificació matemàtica (especialment l'ús de log₂ a la mesura d'unicitat i la fórmula logarítmica a la d'eficiència).
- **Flags de generació**: el suport per a `wall` i `multigoal` permet explorar classes de puzzles molt més diverses sense canviar el codi.

## Limitacions i possibles millores

- La **generació directa** no garanteix resolubilitat per construcció. Això significa que una part dels intents es descarta per ser irresolubles, especialment al nivell `hard`. Un enfocament que parteixi de la solució i "desfaci" moviments garantiria resolubilitat del 100% dels intents. Hem fet un intent d'implementar-ho però és més costós en quant a recursos i temps i ens hem decantat pel nostre generate actual, però és una solució per arreglar aquest problema.
- L'avaluació amb límit de 200.000 posicions pot "subestimar" la dificultat de puzzles molt grans on la solució no és assolible dins del límit. La mesura de colls d'ampolla, en particular, pot estar incompleta en grafs tallats.
- El sistema admet **múltiples objectius** via el flag `multigoal`, però l'estimació de l'A* suma simplement les distàncies de les peces objectiu. En casos on cal moure la peça A per fer lloc a la peça B, l'estimació pot ser massa optimista, cosa que redueix l'eficiència de l'A* en puzzles multigoal complexos.

---

---

<div id="contrib" />

## Crèdits i Autors

Projecte Base original:
- L'arquitectura inicial, la interfície de l'API i la idea original del projecte són obra de [Pau Fernández (pauek)](https://github.com/pauek/klotski).

Humans:

- _Alejandro Duems_
- _Hèctor Guevara_

LLMs:

- _Claude Sonnet 4.6_: programació i documentació.
- _Google Gemini 3.1_: programació i documentació.
