"""Enfrenta dos bots con los equipos de la final de Frankfurt y cuenta victorias.

Uso (con Showdown local en el puerto 8000):
  python bots/experimento.py TIPO_ERIC TIPO_SEBA N [PREVIEW_ERIC] [PREVIEW_SEBA]
TIPO: reglas | dano | aleatorio. PREVIEW: 4 especies separadas por comas (2 líderes y
2 de reserva) o "-" para el preview automático. Ejemplo:
  python bots/experimento.py reglas reglas 200 garchomp,gholdengo,volcarona,incineroar farigiraf,garchomp,torkoal,sylveon
"""
import asyncio
import random
import sys
import time
import uuid
from pathlib import Path

from poke_env import AccountConfiguration, LocalhostServerConfiguration
from poke_env.player import RandomPlayer

from bot_reglas import BotReglas, Calculadora

FMT = "gen9championsvgc2026regmc"
EQ = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "final_frankfurt"


class Aleatorio(RandomPlayer):
    def teampreview(self, battle):
        return self.random_teampreview(battle)


def crear(tipo, equipo, rival, calc, nombre, preview=None):
    cuenta = AccountConfiguration(f"{nombre}{uuid.uuid4().hex[:6]}", None)
    comun = dict(account_configuration=cuenta, battle_format=FMT,
                 server_configuration=LocalhostServerConfiguration, max_concurrent_battles=10)
    if tipo == "aleatorio":
        return Aleatorio(team=equipo, **comun)
    if tipo == "dano":
        return BotReglas(equipo_propio=equipo, equipo_rival=rival, calculadora=calc,
                         solo_dano=True, temperatura=0, **comun)
    return BotReglas(equipo_propio=equipo, equipo_rival=rival, calculadora=calc, preview=preview, **comun)


async def serie(tipo_a, tipo_b, eq_a, eq_b, n, calc):
    """A juega eq_a y B eq_b. Devuelve victorias de A."""
    pa = sys.argv[4].split(",") if len(sys.argv) > 4 and sys.argv[4] != "-" else None
    pb = sys.argv[5].split(",") if len(sys.argv) > 5 and sys.argv[5] != "-" else None
    a = crear(tipo_a, eq_a, eq_b, calc, "A", pa)
    b = crear(tipo_b, eq_b, eq_a, calc, "B", pb)
    await a.battle_against(b, n_battles=n)
    return a.n_won_battles, a.n_finished_battles


async def main():
    tipo_eric, tipo_seba, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
    eric, seba = (EQ / "eric.txt").read_text(), (EQ / "sebastian.txt").read_text()
    random.seed(0)
    t = time.time()
    with Calculadora() as calc:
        g, total = await serie(tipo_eric, tipo_seba, eric, seba, n, calc)
    print(f"Eric ({tipo_eric}) vs Sebastian ({tipo_seba}): Eric gana {g}/{total} "
          f"({100*g/max(total,1):.0f} %) en {time.time()-t:.0f}s")


asyncio.run(main())
