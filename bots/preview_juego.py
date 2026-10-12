"""B1 (prototipo): team preview resuelto como juego de suma cero por simulación.

Un *plan* es (líder 1, líder 2, reserva 1, reserva 2): 15 formas de elegir 4 de 6
y 6 parejas de líderes por cada una, 90 planes por equipo. Simular 90 × 90 casillas
es demasiado, así que se usa *double oracle*:

1. Se empieza con pocos planes por lado y se simula la tabla entre ellos.
2. Se resuelve el equilibrio de Nash de esa tabla (estrategias mixtas).
3. Para cada lado se busca la mejor respuesta entre sus 90 planes contra la mezcla
   del rival (cribado barato con pocas partidas y refinado de los mejores).
4. Si la mejor respuesta mejora el valor del juego, se añade y se repite.

El resultado: la mezcla de planes de cada lado y el porcentaje del matchup cuando
los dos juegan su mejor estrategia de preview (con el bot de reglas pilotando).

Uso (con Showdown local):
  python -m bots.preview_juego --n-casilla 40 --n-criba 12
"""

import argparse
import asyncio
import itertools
import json
import math
import random
import time
from pathlib import Path

import numpy as np

from calculo import Calculadora
from importar_showdown import normalizar_id

from .equipos import leer_equipo
from .experimento import EQ, serie, wilson


def planes(texto_equipo, datos):
    """Los 90 planes de un equipo de 6: 4 de 6 y la pareja de líderes entre ellos."""
    especies = [normalizar_id(e) for e in leer_equipo(texto_equipo, datos)]
    resultado = []
    for cuatro in itertools.combinations(especies, 4):
        for lideres in itertools.combinations(cuatro, 2):
            reservas = [e for e in cuatro if e not in lideres]
            resultado.append(tuple(lideres) + tuple(reservas))
    return resultado


def resolver_juego(matriz, iteraciones=20000):
    """Equilibrio de un juego de suma cero (filas maximizan) por regret matching.

    Devuelve (mezcla filas, mezcla columnas, valor). Sin dependencias además de numpy.
    """
    m = np.asarray(matriz, dtype=float)
    filas, columnas = m.shape
    reg_f, reg_c = np.zeros(filas), np.zeros(columnas)
    suma_f, suma_c = np.zeros(filas), np.zeros(columnas)
    for _ in range(iteraciones):
        pf = np.maximum(reg_f, 0)
        pf = pf / pf.sum() if pf.sum() > 0 else np.full(filas, 1 / filas)
        pc = np.maximum(reg_c, 0)
        pc = pc / pc.sum() if pc.sum() > 0 else np.full(columnas, 1 / columnas)
        suma_f += pf
        suma_c += pc
        valor_f = m @ pc            # pago de cada fila contra la mezcla de columnas
        valor_c = pf @ m            # pago (para filas) de cada columna
        reg_f += valor_f - pf @ valor_f
        reg_c += (pf @ m @ pc) - valor_c
    xf, xc = suma_f / suma_f.sum(), suma_c / suma_c.sum()
    return xf, xc, float(xf @ m @ xc)


class Simulador:
    """Guarda resultados por casilla (plan A, plan B) y simula lo que falte."""

    def __init__(self, eq_a, eq_b, calc, *, puerto=8000, concurrencia=4, seed=0):
        self.eq_a, self.eq_b, self.calc = eq_a, eq_b, calc
        self.puerto, self.concurrencia, self.seed = puerto, concurrencia, seed
        self.resultados = {}  # (plan_a, plan_b) -> [victorias de A, partidas]
        self.partidas = 0

    async def _jugar(self, pa, pb, n, intentos=4):
        for intento in range(intentos):
            try:
                victorias, total = await serie("reglas", "reglas", self.eq_a, self.eq_b, n, self.calc,
                                               preview_a=list(pa), preview_b=list(pb),
                                               seed=self.seed + self.partidas, puerto=self.puerto)
                break
            except ConnectionError:
                # Con mucha carga, la comprobación rápida del servidor puede fallar.
                if intento == intentos - 1:
                    raise
                await asyncio.sleep(3 * (intento + 1))
        celda = self.resultados.setdefault((pa, pb), [0, 0])
        celda[0] += victorias
        celda[1] += total
        self.partidas += total

    async def asegurar(self, pedidos):
        """pedidos: [(plan_a, plan_b, n mínimo)]. Simula en paralelo lo que falte."""
        sem = asyncio.Semaphore(self.concurrencia)

        async def uno(pa, pb, n):
            falta = n - self.resultados.get((pa, pb), [0, 0])[1]
            if falta > 0:
                async with sem:
                    await self._jugar(pa, pb, falta)

        await asyncio.gather(*(uno(*p) for p in pedidos))

    def tasa(self, pa, pb):
        v, t = self.resultados.get((pa, pb), [0, 0])
        return (v + 1) / (t + 2)  # suavizado de Laplace para casillas con pocas partidas


def _repartir(mezcla, soporte, n):
    """Reparte n partidas entre los planes con peso de la mezcla (al menos 1 a cada uno)."""
    activos = [(p, w) for p, w in zip(soporte, mezcla) if w > 0.02]
    total = sum(w for _, w in activos)
    return [(p, max(1, round(n * w / total)), w / total) for p, w in activos]


async def mejor_respuesta(sim, lado, candidatos, soporte_rival, mezcla_rival, n_criba, n_refino, top=3):
    """Mejor plan de ``lado`` ('a' o 'b') contra la mezcla del rival."""
    reparto = _repartir(mezcla_rival, soporte_rival, n_criba)

    def pedido(plan, rival, n):
        return (plan, rival, n) if lado == "a" else (rival, plan, n)

    def valor(plan):
        total = 0.0
        for rival, _, peso in reparto:
            pa, pb = (plan, rival) if lado == "a" else (rival, plan)
            t = sim.tasa(pa, pb)
            total += peso * (t if lado == "a" else 1 - t)
        return total

    await sim.asegurar([pedido(p, r, n) for p in candidatos for r, n, _ in reparto])
    mejores = sorted(candidatos, key=valor, reverse=True)[:top]
    reparto_fino = _repartir(mezcla_rival, soporte_rival, n_refino)
    await sim.asegurar([pedido(p, r, n) for p in mejores for r, n, _ in reparto_fino])
    mejor = max(mejores, key=valor)
    return mejor, valor(mejor)


async def double_oracle(eq_a, eq_b, calc, *, iniciales_a, iniciales_b, n_casilla=40, n_criba=12,
                        n_refino=40, max_iter=5, margen=0.03, puerto=8000, concurrencia=4, log=print):
    todos_a, todos_b = planes(eq_a, calc.datos), planes(eq_b, calc.datos)
    soporte_a, soporte_b = list(iniciales_a), list(iniciales_b)
    sim = Simulador(eq_a, eq_b, calc, puerto=puerto, concurrencia=concurrencia)
    historial = []
    for it in range(1, max_iter + 1):
        await sim.asegurar([(pa, pb, n_casilla) for pa in soporte_a for pb in soporte_b])
        matriz = [[sim.tasa(pa, pb) for pb in soporte_b] for pa in soporte_a]
        xa, xb, valor = resolver_juego(matriz)
        br_a, v_a = await mejor_respuesta(sim, "a", todos_a, soporte_b, xb, n_criba, n_refino)
        br_b, v_b = await mejor_respuesta(sim, "b", todos_b, soporte_a, xa, n_criba, n_refino)
        historial.append({"iteracion": it, "valor": valor, "partidas": sim.partidas,
                          "mejor_respuesta_a": [list(br_a), v_a], "mejor_respuesta_b": [list(br_b), v_b]})
        log(f"[{it}] valor A {valor:.3f} | mejor resp. A {v_a:.3f} {br_a} | "
            f"mejor resp. B {1 - v_b:.3f} (para A) {br_b} | {sim.partidas} partidas")
        nuevo = False
        if v_a > valor + margen and br_a not in soporte_a:
            soporte_a.append(br_a)
            nuevo = True
        if v_b > (1 - valor) + margen and br_b not in soporte_b:
            soporte_b.append(br_b)
            nuevo = True
        if not nuevo:
            break
    await sim.asegurar([(pa, pb, n_casilla) for pa in soporte_a for pb in soporte_b])
    matriz = [[sim.tasa(pa, pb) for pb in soporte_b] for pa in soporte_a]
    xa, xb, valor = resolver_juego(matriz)
    return {
        "valor_a": valor,
        "mezcla_a": sorted(([list(p), float(w)] for p, w in zip(soporte_a, xa) if w > 0.01), key=lambda x: -x[1]),
        "mezcla_b": sorted(([list(p), float(w)] for p, w in zip(soporte_b, xb) if w > 0.01), key=lambda x: -x[1]),
        "matriz": {"filas": [list(p) for p in soporte_a], "columnas": [list(p) for p in soporte_b],
                   "tasa_a": [[round(sim.tasa(pa, pb), 3) for pb in soporte_b] for pa in soporte_a],
                   "partidas": [[sim.resultados[(pa, pb)][1] for pb in soporte_b] for pa in soporte_a]},
        "partidas": sim.partidas,
        "historial": historial,
    }


def plan_arg(texto):
    partes = [normalizar_id(p) for p in texto.split(",")]
    if len(partes) != 4:
        raise argparse.ArgumentTypeError("Un plan son 4 especies: 2 líderes y 2 reservas")
    return tuple(partes)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--equipo-a", default=str(EQ / "eric.txt"))
    p.add_argument("--equipo-b", default=str(EQ / "sebastian.txt"))
    p.add_argument("--inicial-a", type=plan_arg, action="append",
                   help="Plan inicial de A (repetible). Por defecto, uno al azar.")
    p.add_argument("--inicial-b", type=plan_arg, action="append")
    p.add_argument("--n-casilla", type=int, default=40)
    p.add_argument("--n-criba", type=int, default=12)
    p.add_argument("--n-refino", type=int, default=40)
    p.add_argument("--max-iter", type=int, default=5)
    p.add_argument("--concurrencia", type=int, default=4)
    p.add_argument("--puerto", type=int, default=8000)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--salida", help="Guardar el resultado en JSON")
    args = p.parse_args(argv)
    eq_a, eq_b = Path(args.equipo_a).read_text(), Path(args.equipo_b).read_text()
    random.seed(args.seed)
    inicio = time.time()
    with Calculadora() as calc:
        ini_a = args.inicial_a or [random.choice(planes(eq_a, calc.datos))]
        ini_b = args.inicial_b or [random.choice(planes(eq_b, calc.datos))]
        res = asyncio.run(double_oracle(
            eq_a, eq_b, calc, iniciales_a=ini_a, iniciales_b=ini_b, n_casilla=args.n_casilla,
            n_criba=args.n_criba, n_refino=args.n_refino, max_iter=args.max_iter,
            puerto=args.puerto, concurrencia=args.concurrencia))
    print(f"\nValor del matchup para A: {100 * res['valor_a']:.1f} %  "
          f"({res['partidas']} partidas, {time.time() - inicio:.0f} s)")
    for lado in ("a", "b"):
        print(f"Mezcla de {lado.upper()}:")
        for plan, peso in res[f"mezcla_{lado}"]:
            print(f"  {100 * peso:5.1f} %  líderes {plan[0]} + {plan[1]}, reserva {plan[2]} + {plan[3]}")
    if args.salida:
        Path(args.salida).write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
