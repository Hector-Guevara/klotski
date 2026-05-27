# Klotski! (Pràctica 2 d'AP2, Primavera de 2026)

# Visió Global del Projecte

## Què és Klotski?

El **Klotski** és un trencaclosques clàssic de peces lliscants: un conjunt de peces de formes i mides diverses col·locades sobre un taulell rectangular, on l'objectiu és moure una peça concreta fins a una posició determinada, desplaçant la resta per fer-li camí. Les peces només poden lliscar en una de les quatre direccions carinals (N, S, E, W) i no poden solapar-se ni sortir del taulell.

El que fa interessant aquest joc des d'un punt de vista computacional és que el seu espai d'estats pot créixer exponencialment amb el nombre de peces i la mida del taulell — el Klotski original en la seva configuració clàssica té una solució òptima de **116 moviments** i desenes de milers d'estats accessibles. Això significa que un humà que intenti resoldre-ho "per força bruta" pot trigar hores, mentre que un algorisme ben dissenyat ho resol en fraccions de segon.

La variant que implementem en aquesta pràctica és més general que el joc comercial: les peces poden tenir qualsevol forma de poliominó fins a mida 4 (no només rectangles), el taulell pot tenir qualsevol dimensió N×M, i es pot incloure parets (caselles bloquejades). Això ens permet explorar un espai de disseny molt més ric i generar puzzles originals que no existeixen en cap joc comercial actual.

## Objectiu del Projecte

L'objectiu d'aquesta pràctica és construir un **sistema complet i col·laboratiu** que permeti:

1. **Generar** puzzles de Klotski de forma automàtica en tres nivells de dificultat (`easy`, `medium`, `hard`), garantint sempre que siguin resolubles mitjançant scrambling reversible.
2. **Avaluar** la qualitat i dificultat de cada puzzle mitjançant cinc mètriques objectives derivades del seu graf d'estats, combinades en una puntuació final de 0 a 5 estrelles.
3. **Resoldre** qualsevol puzzle de forma òptima (nombre mínim de moviments) amb un algorisme A* que utilitza una clau canònica híbrida per reduir dràsticament l'espai de cerca.
4. **Visualitzar** l'estat del taulell i la solució, tant de forma interactiva (PyGame) com en GIF animat i en un graf 3D força-dirigit interactiu al navegador.
5. **Interactuar** amb un repositori compartit per descarregar, puntuar i pujar puzzles, contribuint a un rànking col·lectiu que evoluciona a mesura que tots els participants envien puzzles i valoracions.

El resultat és un pipeline complet: des de la generació aleatòria fins a la publicació col·laborativa, passant per la resolució òptima i la visualització. Cada mòdul ha estat dissenyat per ser independent i reutilitzable, de manera que combinar-los és natural i expressiu.

***

## Principals Desafiaments Tècnics

### Garantia de resolubilitat

Un puzzle generat aleatòriament té moltes probabilitats de ser **irresoluble**: les peces poden quedar encaixades sense cap seqüència de moviments que permeti assolir l'objectiu. Comprovar la resolubilitat a posteriori (generant el graf i verificant si hi ha camí) és car i no garantit.

La solució adoptada és el **scrambling reversible**: en lloc de col·locar les peces a l'atzar i esperar que el resultat sigui resoluble, es construeix primer un estat **resolt** (la meta) i a continuació es fa una caminata aleatòria reversible sobre el graf d'estats reals. L'estat inicial del puzzle és, per construcció, assolible des de la meta. No cal verificar res: la resolubilitat és una propietat estructural del procés de generació, no una condició a comprovar.

Addicionalment, el scrambler evita l'últim moviment invers (per no oscil·lar entre dos estats) i prioritza estats no visitats (per explorar l'espai eficientment). El resultat és l'estat accessible més allunyat de la meta en termes de distància BFS, cosa que maximitza la dificultat del puzzle generat.

### Ordenació canònica de peces

La classe `Puzzle` exigeix que les peces estiguin en **ordre canònic** — ordenades lexicogràficament per `(forma, posició_inicial)`. Això és necessari per a la unicitat de representació: dos puzzles idèntics han de tenir el mateix JSON i el mateix hash SHA-256. Sense aquesta unicitat, detectar duplicats al repositori seria impossible.

Però l'ordre canònic complica la generació: cada cop que s'afegeix una peça al taulell, cal reordenar tot el conjunt de peces conjuntament amb les posicions associades, ja que l'índex de cada peça determina la seva posició dins del vector `start`. Si s'afegeix una peça amb forma "petita" al final però lexicogràficament hauria d'anar primera, tots els índexos canvien i cal reindexar els objectius.

### Explosió de l'espai d'estats

Per a puzzles densos, l'espai pot superar els centenars de milers d'estats. La causa és combinatòria: si hi ha $k$ peces intercanviables i $n$ posicions possibles, l'espai creix com $\binom{n}{k}$. El Klotski original té ~200.000 estats accessibles.

El sistema utilitza una **clau canònica híbrida** a l'A* i al generador de grafs: les peces no-objectiu idèntiques s'agrupen per forma (no per identitat), la qual cosa redueix dràsticament l'espai de cerca sense perdre l'optimalitat de la solució. Dues configuracions que difereixen únicament en quina de les peces 1×1 indistingibles ocupa cada posició es tracten com el mateix estat — perquè des del punt de vista del puzzle, ho són.

### Mesura de dificultat objectiva

Definir "dificultat" de forma objectiva és no trivial. Un puzzle amb solució de 50 moviments pot ser senzill si tots els moviments són evidents; un de 20 moviments pot ser diabòlic si requereix una seqüència contraintuïtiva. Per capturar aquesta riquesa, s'ha optat per una **puntuació ponderada de cinc mètriques** derivades del graf d'estats, cadascuna capturant un aspecte diferent i complementari: longitud de la solució, mida de l'espai, unicitat dels camins a la meta, profunditat relativa del camí òptim i estructura de colls d'ampolla.

***

## Estructura del Sistema i Comandos

El projecte s'organitza en mòduls independents. A continuació es mostra el flux típic d'ús i els comandos corresponents.

### Inicialització de l'entorn

```bash
pixi shell
# Per inicialitzar el pixi, no funcionarà si no comencem per aquesta comanda.
# Cal tenir el pixi i totes les dependències especificades a l'enunciat instal·lades.
```

### Generació d'un puzzle

```bash
python src/generate.py <easy|medium|hard> <nom_puzzle>
```

Exemple:
```bash
python src/generate.py hard puzzles/puzzle_dificil
# Resultat: puzzles/puzzle_dificil.json
```

### Resolució

```bash
python src/solve.py <puzzle.json>
# Resultat: puzzle.sol.json
```

### Avaluació de qualitat

```bash
python src/eval.py <puzzle.json>
```

### Visualització estàtica (PNG)

```bash
python src/image.py <puzzle.json>
```

### Joc interactiu

```bash
python src/play.py <puzzle.json>
```

### Animació GIF de la solució

```bash
python src/movie.py <puzzle.json> <puzzle.sol.json> [output.gif]
```

### Generació i visualització del graf 3D

```bash
python src/graph.py <puzzle.json>
python src/3D_view.py <puzzle.graphml> [puzzle.sol.json]
```

### Interacció amb el repositori compartit

```bash
# Descarregar tots els puzzles
python src/download.py

# Descarregar un puzzle específic per ID
python src/download.py <puzzle_id>

# Pujar un puzzle
python src/upload.py <puzzle.json> <token>

# Avaluar i puntuar un puzzle del repositori
python src/rate.py <puzzle_id> <token>

# Puntuar tots els puzzles del repositori
python src/rate_all.py <token> [--skip-errors]
```

***

# Descripció Detallada dels Mòduls

## Representació de Dades: `puzzle.py`

### Què fa

Defineix els tres tipus fonamentals del sistema:

- **`Piece`**: forma d'una peça com a tupla de coordenades relatives normalitzades. La normalització garanteix que `min(x) == 0` i `min(y) == 0`, és a dir, la peça sempre es representa ancorada a l'origen, independentment d'on estigui col·locada al taulell.
- **`State`**: configuració del taulell en un instant donat — simplement una tupla de posicions, una per peça, en el mateix ordre que les peces del puzzle. La separació entre `Puzzle` (forma + objectiu) i `State` (posicions) permet reutilitzar la definició del puzzle per a milers d'estats sense duplicar dades.
- **`Puzzle`**: el trencaclosques complet: dimensions `W × H`, parets, peces, estat inicial i llista d'objectius `(índex_peça, posició_meta)`. Inclou mètodes de serialització a JSON i càlcul d'un hash SHA-256 únic.

### Decisions de disseny destacades

**Immutabilitat total** (`frozen=True`): totes tres classes són immutables i hashables. Això permet usar estats com a claus de diccionari directament, cosa fonamental per a l'A* i per al generador de grafs, que necessiten una taula de visitats eficient. Un `State` pot ser clau d'un diccionari de distàncies sense cap conversió extra.

**Validació a `__post_init__`**: `Puzzle` verifica en construcció que les peces no se solapen, que estan en ordre canònic, que les parets estan dins del taulell i que els índexos d'objectiu són vàlids. Qualsevol `Puzzle` que existeixi al sistema és, per definició, consistent. No és possible crear un puzzle invàlid sense una excepció explícita — això elimina una classe sencera de bugs subtils que podrien aparèixer molt més tard durant l'exploració del graf.

**Ordre canònic de peces**: les peces s'ordenen per `(forma, posició_inicial)`. Aquesta restricció és la que garanteix que dos puzzles amb les mateixes peces en les mateixes posicions però generats en ordre diferent produeixin el mateix JSON i el mateix hash SHA-256. Sense aquesta unicitat, el repositori podria acumular duplicats i les comparacions entre puzzles serien inconsistents.

**`Piece.normalized`**: mètode estàtic que normalitza coordenades arbitràries en una `Piece` vàlida. Permet al generador treballar amb coordenades absolutes i normalitzar al final, sense haver de gestionar manualment l'offset mínim.

***

## Lògica del Joc: `logic.py`

### Què fa

Implementa tota la mecànica del joc: comprovar si un moviment és vàlid, aplicar-lo, calcular el màxim lliscament d'una peça en una direcció, llistar tots els moviments possibles des d'un estat i verificar si un estat és la meta.

### Decisions de disseny destacades

**`can_move` per sobre de `apply_move`**: la separació entre verificació i aplicació permet al codi client (A*, generador de grafs, scrambler) consultar la validesa sense generar estats intermedis. Això és especialment útil a `max_slide`, que calcula fins on pot lliscar una peça de forma eficient iterant `can_move` fins al bloqueig, i a `play.py`, que necessita saber el rang de lliscament per limitar l'arrossegament del ratolí.

**Moviments d'un sol pas**: `possible_moves` retorna moviments de distància 1 (`(piece_idx, direction, dist=1)`). Aquesta granularitat és la correcta per construir el graf d'estats: cada aresta del graf correspon a exactament un moviment elemental, cosa que garanteix que la distància en el graf és exactament el nombre de moviments. `apply_move` accepta distàncies majors per permetre operacions de lliscament complet des del joc interactiu, amb validació pas a pas.

**`_occupied_by_others`**: en lloc de mantenir un conjunt global d'ocupació sincronitzat amb l'estat, es reconstrueix per a cada peça en cada comprovació. Això simplifica el codi eliminant un estat auxiliar que caldria actualitzar en cada `apply_move`, i és perfectament acceptable per a taulells de mida 4–7×4–7 amb 5–15 peces.

**`replay_moves`**: permet reproduir una seqüència de moviments des de l'estat inicial i obtenir tots els estats intermedis. `movie.py` el fa servir per animar la solució frame a frame; `3D_view.py` el fa servir per identificar les arestes del camí òptim al graf i ressaltar-les en groc.

***

## Generació de Puzzles: `generate.py`

### Què fa

Genera puzzles nous en format `.json` a partir d'un nivell de dificultat (`easy`, `medium`, `hard`). La interfície és simple:

```bash
python src/generate.py medium puzzles/el_meu_puzzle
```

El programa escull automàticament les dimensions del taulell, la densitat d'ocupació, les formes de les peces i la posició objectiu en funció del nivell, sense que l'usuari hagi d'especificar res més.

### El catàleg de formes i els pesos per nivell

El sistema inclou **27 formes** de poliominós fins a mida 4 (dòminos, triòminós I i L, tetròminós O, I, T, L, J, S i Z en totes les orientacions). Cada nivell té un vector de pesos que controla la distribució de mides de peça triades:

| Nivell | Mides preferides | Densitat | Parets |
|--------|-----------------|----------|--------|
| easy   | Petites (mida 1–2) | 55%   | No     |
| medium | Mitjanes (mida 2–3) | 70%  | No     |
| hard   | Grans (mida 3–4)   | 72%  | Sí     |

Les peces grans restringeixen més el taulell i generen grafs amb menys camins alternatius — exactament el que fa un puzzle difícil. El `OCUPACIO_OBJECTIU` controla quantes caselles estan ocupades: un taulell al 72% d'ocupació deixa molt poc espai de maniobra, cosa que força seqüències de moviments llargues i contraintuïtives.

### El scrambling reversible: garantia de resolubilitat per construcció

Aquesta és la peça arquitectònica més important del generador. El problema fonamental és que col·locar peces a l'atzar i comprovar després si el puzzle és resoluble és ineficient i no garantit — la majoria de configuracions aleatòries denses no són resolubles.

L'alternativa elegent és **construir el puzzle al revés**:

1. Es determina la **posició meta** de la peça objectiu (la peça més gran, col·locada en el percentil de posicions més llunyà de la seva posició inicial).
2. Es construeix un **estat resolt**: totes les peces col·locades de manera que la peça objectiu ja estigui a la meta.
3. Es fa una **caminata aleatòria** sobre el graf d'estats reals des de l'estat resolt: en cada pas es tria un moviment aleatori dels possibles, evitant l'últim moviment invers (per no retrocedir immediatament) i prioritzant estats no visitats. La caminata s'atura quan ha fet prou passos o ha explorat tots els estats accessibles des de la meta.
4. L'**estat inicial** del puzzle és l'estat de la caminata més allunyat de la meta en termes de distància BFS.

La garantia de resolubilitat és **per construcció i matemàticament exacta**: qualsevol estat assolit per la caminata és, per definició, assolible des de la meta amb la seqüència inversa de moviments. No cal explorar el graf complet per verificar-ho — ja se sap que la solució existeix i quin és el seu cost màxim (la longitud de la caminata).

Comparat amb l'enfocament anterior (col·locar peces a l'atzar i descartar les configuracions no resolubles), el scrambling reversible elimina completament la necessitat de verificació posterior i garanteix que cada intent de generació produeixi un puzzle resoluble. Això fa que el generador sigui molt més ràpid i fiable, especialment per al nivell `hard` on les configuracions resolubles eren molt escasses.

### Selecció del millor puzzle entre múltiples intents

El sistema fa fins a `max_intents` intents (40 per a `easy`, 60 per a `medium`, 100 per a `hard`) i avalua cada puzzle generat amb `eval.py`. Es guarda el millor (màxima puntuació) i s'atura quan s'assoleix la `puntuacio_minima` del nivell. Si cap intent arriba a la puntuació mínima, es retorna el millor trobat amb un avís — el programa mai falla per no trobar prou bé.

La telemetria en temps real mostra cada intent amb el nombre d'estats explorats i la puntuació, de manera que l'usuari pot veure com progressa la cerca:

```
  →  Intent   3/60: Generant...  Avaluant... ✅ RESOLUBLE! (1842 estats) — Nota: 2.31
  →  Intent   4/60: Generant...  Avaluant... ✅ RESOLUBLE! (3104 estats) — Nota: 2.87
  ✓ Puntuació objectiu assolida a l'intent 4.
```

***

## Resolució Òptima: `solve.py`

### Què fa

Resol qualsevol puzzle de forma **òptima** (nombre mínim de moviments) i genera un fitxer `.sol.json` amb la seqüència de moviments. La solució és exacta: cap altre algorisme podria trobar una seqüència més curta.

### L'algorisme A* i la seva heurística

L'A* és un algorisme de cerca informada que explora l'espai d'estats per ordre de `f(n) = g(n) + h(n)`, on `g(n)` és el cost real fins a l'estat `n` (nombre de moviments realitzats) i `h(n)` és una estimació del cost restant fins a la meta.

La heurística triada és la **distància de Manhattan** de la peça objectiu fins a la seva posició meta:

```
h(estat) = |x_actual - x_meta| + |y_actual - y_meta|
```

Aquesta heurística és **admissible** (no sobreestima mai el cost real) perquè en el millor dels casos imaginable — sense cap obstacle, en línia recta — la peça objectiu trigaria exactament tants moviments com la seva distància Manhattan. La realitat sempre és igual o pitjor. Amb una heurística admissible, l'A* garanteix trobar sempre la solució **òptima** — mai una seqüència de moviments més llarga del mínim necessari.

En la pràctica, la heurística redueix dràsticament el nombre d'estats explorats: en lloc de expandir tots els estats a distància $d$ de l'inicial (com faria un BFS), l'A* es focalitza en els que semblen prometedors (els que estan a poca distància Manhattan de la meta). Per a puzzles de nivell `medium` típics, l'A* pot trobar la solució òptima explorant menys d'un 10% dels estats que exploraria un BFS complet.

### La clau canònica híbrida: reducció de l'espai de cerca

El component més crític per a l'eficiència de l'A* és la gestió dels estats visitats. Si usem `State` directament com a clau, dos estats que difereixen únicament en quina de les peces 1×1 indistingibles ocupa cada posició es tractarien com a estats **diferents**, duplicant inútilment el treball.

La solució és la **clau canònica híbrida** (`canonical_key`):

- Les **peces objectiu** es marquen per identitat exacta (`GOAL, índex`). La seva posició individual importa perquè l'objectiu depèn de la seva ubicació concreta.
- Les **peces no-objectiu idèntiques** s'agrupen per forma (`NORMAL, coords`) i les seves posicions s'ordenen. No importa *quina* peça 1×1 ha mogut — importa *on estan* les peces d'aquella forma.

Per exemple, en un puzzle amb cinc peces 1×1 no-objectiu, en lloc de tractar les $5! = 120$ permutacions com a estats diferents, la clau canònica les col·lapsa en un sol estat. Això pot reduir l'espai de cerca en un factor de $k!$ per cada grup de $k$ peces idèntiques, cosa que marca la diferència entre una cerca de minuts i una de mil·lisegons.

La clau híbrida és **consistent amb l'optimalitat**: dos estats amb la mateixa clau canònica estan a la mateixa distància de la meta (perquè les peces objectiu estan en la mateixa posició), de manera que col·lapsar-los no afecta la longitud de la solució trobada.

### Format de la solució

```json
[[2, "W", 1], [0, "N", 1], [3, "E", 2], ...]
```

Cada element és `[índex_peça, direcció, distància]`. La distància és sempre 1 (un moviment elemental per pas), cosa que garanteix la compatibilitat directa amb `movie.py` i `3D_view.py`.

***

## Generació del Graf d'Estats: `graph.py`

### Què fa

Explora tot l'espai d'estats accessible des de l'estat inicial i construeix el **graf dirigit complet** amb `graph-tool`, una biblioteca C++ amb bindings Python d'altíssim rendiment. Cada node és un estat possible del taulell; cada aresta és un moviment elemental que connecta dos estats.

El graf resultant es pot desar en format `.graphml` per a ús posterior (visualització 3D, anàlisi) o es pot usar directament en memòria per `eval.py`.

### Estratègia de construcció en bloc: per què és tan ràpid

La diferència de rendiment entre construir un graf element per element i fer-ho en bloc és de **1 a 2 ordres de magnitud**. La raó és que cada crida a una funció de C++ des de Python té un overhead fix (gestió del GIL, conversió de tipus, etc.) que per a milers d'operacions s'acumula significativament.

El procés adoptat elimina aquest overhead:

1. **Exploració pura en Python**: es fa un DFS des de l'estat inicial, acumulant totes les arestes `(idx_origen, idx_destí)` en una llista Python i les metadades de cada node (si és inicial, si és meta, la seva clau canònica) en arrays paral·lels. Cap crida a `graph-tool` durant aquesta fase.
2. **Construcció en bloc**: una sola crida a `g.add_vertex(n)` crea tots els nodes alhora, i una sola crida a `g.add_edge_list(edges)` crea totes les arestes. Internament, `graph-tool` processa la llista amb codi C++ vectoritzat.
3. **Assignació de propietats en bloc**: les propietats booleanes (`is_goal`, `is_start`) s'assignen com a arrays NumPy directament als PropertyMaps de `graph-tool`, sense iterar sobre els nodes un per un.

El resultat és que per a un graf de 5.000 nodes i 30.000 arestes, la construcció tarda menys d'un segon, mentre que la construcció incremental podria trigar 10-30 segons.

### La clau canònica compartida amb `solve.py`

`graph.py` importa `canonical_key` de `solve.py` i la usa per identificar estats. Això garanteix que el graf i l'A* **viuen en el mateix espai d'estats**: un node del graf correspon exactament a un estat canònic que l'A* pot reconèixer, i viceversa. Les mètriques del graf (nombre d'estats, nombre de solucions, distàncies) són directament comparables amb els resultats de l'A*.

Sense aquesta unificació, podrien sorgir inconsistències subtils: el graf podria tenir menys nodes que els estats que l'A* visita (o més), fent que les mètriques no reflectissin la realitat de la cerca.

### El límit d'estats i el seu efecte sobre les mètriques

`generar_graf` accepta un paràmetre opcional `limit_estats`. Quan s'activa (com fa `eval.py` durant la generació per raons de velocitat), l'exploració s'atura en arribar al límit. Això té un efecte **intencionadament conservador** sobre les mètriques:

- `num_estats` serà un **mínim** del nombre real d'estats. Però com que `ESTATS_MAX_REF = 35.000` és molt més gran que el límit `LIMIT_ESTATS = 8.000`, un puzzle que supera el límit ja rep la puntuació màxima en la mètrica d'espai — el comportament és correcte.
- `num_solucions` pot ser 0 si la meta no es troba dins del límit. En aquest cas, `eval.py` té un fallback a l'A* per obtenir la longitud òptima, i estima `num_solucions = 1` (cas conservador).

Quan `graph.py` s'executa directament (sense límit), genera el graf complet per a ús al visualitzador 3D i com a referència de qualitat.

***

## Avaluació de Qualitat: `eval.py`

### Què fa

Assigna una **puntuació de 0.0 a 5.0** a un puzzle combinant cinc mètriques derivades del seu graf d'estats i de la resolució A*. Qualsevol puzzle pot ser avaluat en pocs segons, cosa que permet filtrar-los durant la generació.

### Arquitectura de dues passades amb fallback intel·ligent

| Passada | Eina | Mètriques obtingudes |
|---------|------|---------------------|
| 1 | `generar_graf(limit_estats=8000)` | `num_estats`, `num_solucions`, ponts estructurals |
| 2 | `shortest_distance` (C++) o A* (fallback) | `longitud_optima` |

El sistema és **adaptatiu**: si el node destí és assolible dins del límit de 8.000 estats, la longitud òptima s'obté amb `gt.shortest_distance` en C++ pur (molt ràpid). Si el graf s'ha tallat abans d'arribar al destí, es fa servir `_a_star_real` com a fallback — que malgrat ser Python és ràpid gràcies a la heurística Manhattan, perquè no cal explorar tot l'espai.

### Les cinc mètriques

**Mètrica 1 — Longitud de la solució òptima** (pes 0.35):
La mètrica més discriminant de totes. Una solució de 30 moviments és genuïnament difícil per a un humà; una de 5 és trivial. Normalitzada linealment fins a `LONGITUD_MAX_REF = 90` moviments (el Klotski original té ~116, però per als taulells que generem, 90 és el percentil superior realista).

**Mètrica 2 — Mida de l'espai d'estats** (pes 0.25):
Un espai de cerca gran significa que hi ha moltes configuracions possibles — el jugador pot "perdre's" fàcilment. Normalitzada fins a `ESTATS_MAX_REF = 35.000`. Puzzles que superen el límit de 8.000 durant la generació reben la puntuació màxima en aquesta mètrica per disseny.

**Mètrica 3 — Unicitat de la solució** (pes 0.20):
Menys camins que porten a la meta → el jugador ha de trobar un camí molt específic → el puzzle és més difícil. Usa `1 / log₂(1 + n)`, que dóna exactament 1.0 per a 1 solució i decreix suaument: 2 solucions → 0.63, 10 → 0.29, 100 → 0.15. La base 2 és l'única que garanteix `f(1) = 1.0` sense factors d'escala addicionals — amb base $e$, `1 / ln(2) ≈ 1.44 > 1`, que sortiria del rang `[0, 1]`.

**Mètrica 4 — Profunditat relativa del camí** (pes 0.10):
`log₂(1 + longitud) / log₂(1 + num_estats)`. Recompensa puzzles on el camí òptim és llarg *en relació* a l'espai total: cal explorar profundament per trobar la solució, no només amplament. La versió anterior (`1 - longitud/num_estats`) tenia el defecte oposat — penalitzava els puzzles amb solució llarga en espais grans, exactament els més interessants.

**Mètrica 5 — Ponts estructurals** (pes 0.10):
Un pont al graf és una aresta l'eliminació de la qual el desconnecta: indica que hi ha un moviment concret que és **obligatori** per resoldre el puzzle (un coll d'ampolla). Puzzles amb molts ponts tenen "fases" — el jugador ha de trobar l'aresta clau en cada fase. Es detecten amb `label_biconnected_components` sobre una `GraphView` no dirigida, que evita còpies en memòria (O(1) d'overhead per crear la vista).

### Puntuació final

$$\text{puntuació} = 5.0 \times \left( 0.35 \cdot s_\text{long} + 0.25 \cdot s_\text{esp} + 0.20 \cdot s_\text{uni} + 0.10 \cdot s_\text{ef} + 0.10 \cdot s_\text{ponts} \right)$$

Els pesos sumen exactament 1.0. El factor 5.0 escala el resultat a l'interval `[0, 5]`, compatible amb el sistema d'estrelles del repositori.

***

## Visualització Interactiva: `play.py`

### Què fa

Proporciona una interfície gràfica amb **PyGame** per jugar al puzzle manualment. L'usuari arrossega les peces amb el ratolí; el sistema detecta l'eix de moviment (horitzontal o vertical) un cop superat un llindar de píxels, i en alliberar el botó fa un **snap** a la casella més propera. La pantalla es torna groga quan el puzzle es resol.

### Decisions de disseny destacades

**Detecció d'eix** (`AXIS_THRESHOLD = 8px`): evita que un lleuger tremolor de la mà activi accidentalment el moviment en la direcció equivocada. L'eix només es fixa quan el desplaçament supera el llindar en una direcció.

**Siluetes poligonals amb inset**: les peces no es dibuixen com a rectangles per casella, sinó com a **polígons de silueta** amb un inset configurable (`PIECE_PAD = 3px`). Donada una peça L de tres caselles, el sistema calcula el polígon frontera de la unió de les tres caselles, simplifica els vèrtexs col·lineals (elimina els punts intermedis en arestes rectes) i aplica un inset cap a l'interior. El resultat és una peça visualment unida i clarament diferenciada de les veïnes, amb un aspecte molt més net que dibuixar cada casella per separat.

**Visualització de l'objectiu en dues capes**: les caselles meta es dibuixen com a rectangles arrodonits semitransparents (*dots*) en dues passades — una per sota de les peces (zona gran, 45% de la casella) i una per sobre (punt petit, 15%). D'aquesta manera, l'objectiu sempre és visible independentment de quina peça el tapi: si la peça hi és a sobre, el punt petit confirma on ha d'anar; si no hi és, el dot gran mostra la posició amb claredat.

***

## Animació: `movie.py`

### Què fa

Genera un GIF animat de la solució d'un puzzle, reproduint cada moviment com una animació fluida de la peça lliscant, amb interpolació cúbica **ease-in-out** per a un moviment suau.

### Interpolació ease-in-out

```python
def ease_in_out(t: float) -> float:
    if t < 0.5:
        return 4 * t**3
    return 1 - (-2*t + 2)**3 / 2
```

Aquesta funció és $C^1$ contínua a $t = 0.5$ i té derivada zero als extrems, cosa que produeix un moviment que arrenca i frena suaument — molt més agradable visualment que una interpolació lineal. El resultat és un GIF d'aspecte professional que mostra la seqüència de moviments de forma clara i elegant.

***

## Visualització del Graf 3D: `3D_view.py`

### Què fa

Carrega un fitxer `.graphml`, el converteix al format JSON de la biblioteca JavaScript **3d-force-graph** i serveix una pàgina HTML interactiva des d'un servidor HTTP local. El navegador renderitza el graf com una xarxa força-dirigida en 3D: els nodes s'atreuen i es repel·leixen com partícules físiques fins a assolir un equilibri que revela l'estructura del graf. Si s'afegeix un fitxer de solució, les arestes del camí òptim es ressalten en groc.

La visualització 3D és extraordinàriament útil per entendre l'estructura dels puzzles: els clústers de nodes densament connectats representen "zones" del taulell fàcils d'explorar; les arestes estretes entre clústers representen els colls d'ampolla (ponts) que fan el puzzle difícil. La solució òptima en groc mostra exactament per quins ponts cal passar.

### Servei en memòria

El graf JSON es manté a la classe `ViewerHandler` (atribut de classe compartit) i es serveix directament sense escriure cap fitxer temporal al disc. Això permet tancar el programa amb Ctrl+C sense deixar residus i simplifica el cicle de treball: no cal gestionar fitxers intermedis.

***

## Interacció amb el Repositori: `download.py`, `upload.py`, `rate.py`, `rate_all.py`

### Flux general

El repositori compartit `https://klotski.pauek.dev/api/puzzles` exposa una API REST senzilla:

| Mètode | Endpoint | Acció |
|--------|----------|-------|
| GET | `/api/puzzles` | Llista d'IDs dels 100 millors |
| GET | `/api/puzzles/<id>` | Descarrega un puzzle |
| POST | `/api/puzzles` | Puja un puzzle nou |
| POST | `/api/puzzles/<id>/votes` | Envia una valoració (1–5 estrelles) |

El servidor retorna els puzzles embolcallats en `{"puzzle": {...}, "stars": N}`. Totes les funcions de descàrrega extreuen automàticament la part del puzzle per desar-la en format estàndard local.

`download.py` gestiona tant la descàrrega individual (`download.py <id>`) com la massiva (`download.py` sense arguments), amb detecció de fitxers ja existents per evitar descàrregues redundants.

`upload.py` valida el puzzle localment amb `Puzzle.from_json`, l'avalua amb `eval.py` i avisa si la puntuació és baixa (< 1.0), però permet enviar-lo igualment — la decisió final és de l'usuari.

`rate.py` automatitza la valoració d'un puzzle individual: el descarrega, el puntua amb `eval.py` (arrodonint a enter per compatibilitat amb l'API) i envia la valoració. `rate_all.py` aplica el mateix procés a tots els puzzles del repositori de forma seqüencial, amb gestió d'errors i l'opció `--skip-errors` per continuar malgrat fallades individuals. Executar `rate_all.py` periòdicament manté el rànking del repositori actualitzat amb el criteri d'avaluació propi.

***

# Conclusions

## Assoliments principals

El sistema construït és un pipeline complet i coherent que abasta des de la generació fins a la publicació col·laborativa de puzzles de Klotski. Les decisions d'arquitectura més rellevants — la representació immutable i canònica, el scrambling reversible, la clau híbrida de l'A*, la construcció en bloc del graf i l'avaluació amb límit adaptatiu — responen cadascuna a un repte concret i es reforcen mútuament.

## Punts forts

- **Correctesa per construcció**: el scrambling reversible garanteix resolubilitat sense necessitar verificació posterior, eliminant completament la categoria de bugs "puzzle generat no resoluble".
- **Eficiència a múltiples nivells**: la clau canònica híbrida redueix l'espai de cerca de l'A* en un factor $k!$ per cada grup de peces idèntiques; la construcció en bloc del graf minimitza les crides Python→C++; el límit adaptatiu d'`eval.py` permet avaluar puzzles en pocs segons durant la generació.
- **Modularitat real**: cada fitxer té una responsabilitat única i clara. `eval.py` no necessita saber com s'ha generat el puzzle; `solve.py` no sap res del graf; `play.py` no depèn d'`eval.py`. Les dependències van sempre en la mateixa direcció: `generate` → `eval` → `graph` → `solve` → `logic` → `puzzle`.
- **Mesura de dificultat fonamentada**: les cinc mètriques capturen aspectes complementaris i independents de la dificultat, amb pesos calibrats empíricament sobre els puzzles de mostra disponibles i justificació matemàtica rigorosa (especialment l'ús de log₂ a la mètrica d'unicitat i la fórmula logarítmica simètrica a la mètrica d'eficiència).

## Limitacions i possibles millores

- L'avaluació amb límit de 8.000 estats pot **subestimar** la dificultat de puzzles molt grans on la meta no és assolible dins del límit i el fallback A* és necessari. Una solució seria usar `shortest_distance` directament sobre el graf parcial quan el node inicial i els candidats a meta es troben dins del límit. Però és necessari si ens adaptem als recursos de la situació.
- El sistema actual admet **un sol objectiu** per puzzle. Estendre-ho a múltiples objectius simultanis (com alguns puzzles del repositori que en tenen dos) obriria un espai de disseny molt més ric, però requeriria adaptar l'heurística de l'A* i la detecció de nodes destí al graf.

---

## Referències

Enunciat:



Trencaclosques tipus _sliding blocks_:

- "[Sliding Block Puzzles](https://puzzlebeast.com/slidingblock/index.html)", a PuzzleBeast.

<div id="contrib" />

## Autors

Humans:

- _Hèctor Guevara_
- _Alejandro Duems_

LLMs:

- _Claude Sonnet 4.6_: programació i documentació.
