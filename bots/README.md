# Bots (prototipo C1b)

Prototipo del bot de reglas para dobles. **No está integrado ni testeado todavía**: la tarea 13 lo convierte en un módulo con tests.

- `bot_reglas.py`: bot de poke-env que puntúa cada acción con daño real (`calculo.py`): KO, Fake Out en el primer turno, Protect según la amenaza, Tailwind/Trick Room, setup, Helping Hand, redirección y Mega. Nunca ataca al compañero. Elige con softmax entre las 12 mejores combinaciones. Conoce el equipo rival (hojas abiertas).
- `experimento.py`: enfrenta dos bots con los equipos de `tests/fixtures/final_frankfurt/`.

Requisitos: `pip install poke-env`, `npm ci --prefix calculo` y un Showdown local:

```
git clone --depth 1 https://github.com/smogon/pokemon-showdown
cd pokemon-showdown && npm install && node build
node pokemon-showdown start --no-security 8000
```

Ejemplo (Eric lidera Garchomp + Gholdengo; Sebastian, Farigiraf + Garchomp):

```
python bots/experimento.py reglas reglas 200 garchomp,gholdengo,volcarona,incineroar farigiraf,garchomp,torkoal,sylveon
```

Resultados del prototipo (2026-10-11, 200 partidas por casilla): con el mejor plan de Sebastian, Eric gana en torno al 40 %.
