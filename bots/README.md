# Bot de reglas C1b para dobles

`bots` es un paquete. `BotReglas` puntúa daño real y KO con `calculo.py`,
Fake Out, Protect, control de velocidad, setup, Helping Hand, redirección y Mega.
Conoce los sets de ambos equipos (hojas abiertas). Conserva la puntuación de
C1b y el softmax entre las 12 mejores combinaciones; el control de velocidad
ahora depende de los activos. Penaliza el daño de área al compañero y evita
ataques dirigidos a él.

`bots.equipos.leer_equipo` lee texto Showdown y conserva los puntos Champions.
`bots.evaluacion` contiene `valor_golpe`, `combinar`, `velocidad_efectiva` y
`valorar_control_velocidad`. Se pueden importar también desde `bots`, sin
poke-env, Node ni servidor.

## Instalación y servidor

Requiere Python 3.10 o superior, `poke-env==0.16.1` y la calculadora fijada del
repo. La calculadora requiere Node 18+, y el Showdown actual, Node 22.18+.
Desde la raíz del repo:

```bash
pip install -r requirements.txt
npm ci --prefix calculo
```

Prepara y arranca Showdown en otra terminal:

```bash
git clone --depth 1 https://github.com/smogon/pokemon-showdown
cd pokemon-showdown
npm install
node build
node pokemon-showdown start --no-security 8000
```

Se usa el formato `gen9championsvgc2026regmc`. Si el servidor no responde,
el experimento termina con un mensaje que indica el comando para arrancarlo.

## Experimentos

Desde la raíz del repo:

```bash
python -m bots.experimento --tipo-a reglas --tipo-b aleatorio --n 10 --seed 0
python -m bots.experimento --tipo-a reglas --tipo-b reglas --n 200 --seed 0 \
  --preview-a garchomp,gholdengo,volcarona,incineroar \
  --preview-b farigiraf,garchomp,torkoal,sylveon \
  --replays work/replays
```

- `--equipo-a` / `--equipo-b`: rutas a `.txt` Showdown; por defecto,
  `tests/fixtures/final_frankfurt/eric.txt` y `sebastian.txt`.
- `--tipo-a` / `--tipo-b`: `reglas` (por defecto), `dano` (solo daño,
  temperatura 0) o `aleatorio`.
- `--preview-a` / `--preview-b`: cuatro especies distintas del equipo,
  separadas por comas; las dos primeras son líderes y las dos últimas,
  reservas. Sin esta opción, el bot elige su preview. Se aplica a los tres tipos.
- `--n`: número de partidas (200 por defecto).
- `--seed`: semilla de las decisiones Python (0 por defecto). Showdown usa su
  propia aleatoriedad para daño, precisión, etc.; no garantiza repetir la serie.
- `--puerto`: puerto de Showdown local (8000 por defecto).
- `--replays`: carpeta opcional; guarda un replay HTML por partida desde A.

Imprime victorias de A / partidas terminadas, porcentaje e intervalo de confianza
Wilson del 95 %. `python -m bots.experimento --help` muestra todas las opciones.

Planes de la final para comparar reglas contra reglas:

| Plan | Preview (líderes primero) |
| --- | --- |
| E1 | volcarona,garchomp,gholdengo,incineroar |
| E2 | garchomp,gholdengo,volcarona,incineroar |
| S1 | incineroar,farigiraf,torkoal,garchomp |
| S2 | farigiraf,garchomp,torkoal,sylveon |

## Control de velocidad

Calcula el stat natural Champions con `velocidad.py`, usando la especie actual
(incluida su Mega), puntos y naturaleza del set abierto. Aplica boosts de velocidad,
Scarf ×1,5 si conserva el objeto, Tailwind ×2 en su lado y parálisis ×0,5.
Omite slots vacíos y debilitados; no infiere efectos de habilidades.

Por cada par activo propio-rival, suma +1 si somos más lentos, −1 si somos más
rápidos y 0 si empatamos. Divide por el número de pares para obtener B.
Trick Room vale `0,6 × B`: positivo si predominan los enfrentamientos lentos y
negativo si predominan los rápidos. Vale 0 si ya está activo y repetirlo lo
anularía. Tailwind vale `0,55 × max(0, B)`; vale 0 si ya lo tenemos o hay Trick
Room. Sin pares, ambos valen 0. Los docstrings detallan la fórmula y los truncados.

El bot mezcla dos balances: `0,4 × valor con los activos + 0,6 × valor con los
miembros vivos de cada equipo` (los propios elegidos en el preview y los rivales
vistos). Trick Room y Tailwind duran varios turnos, así que la reserva cuenta: con
solo los activos, Sebastian casi nunca ponía Trick Room al liderar Farigiraf +
Garchomp-Z, aunque su plan es Torkoal y Sylveon bajo Trick Room.

## Cambios

- Cambio forzado: `0,3 × daño que haría quien entra − 0,3 × daño que recibiría`.
- Cambio voluntario: `−0,3 + 0,1 × daño que haría + 0,6 × (amenaza sobre el que sale −
  amenaza sobre el que entra)`. Quien entra no ataca ese turno y se come el golpe.

## Resultados (Eric vs Sebastian, 200 partidas por casilla, 2026-10-12)

| Eric \ Sebastian | S1 (Incineroar + Farigiraf) | S2 (Farigiraf + Garchomp) |
| --- | ---: | ---: |
| E1 (Volcarona + Garchomp) | 73,0 % | 34,0 % |
| E2 (Garchomp + Gholdengo) | 62,0 % | 36,5 % |

Con su mejor plan (S2), Sebastian deja a Eric en torno al 35 %: matchup
desfavorable para Eric, como dicen Eric y PokéAlex.

## Tests

```bash
python -m pytest
```

`tests/test_bots.py` comprueba daño/KO, KO combinado, velocidades, Trick Room,
Tailwind, lectura de los equipos, CLI e intervalos Wilson sin servidor.
La integración opcional ejecuta 10 partidas reglas contra aleatorio con los
fixtures de la final y exige al menos 8 victorias del bot de reglas.

Se omite si falta Node, `calculo/node_modules`, poke-env o un Showdown que responda
en `localhost:8000`. Para otro servidor, usa `SHOWDOWN_URL` (base HTTP/WS o URL
websocket completa):

```bash
SHOWDOWN_URL=ws://localhost:9000/showdown/websocket python -m pytest tests/test_bots.py
```
