"""Enfrenta dos bots: python -m bots.experimento --help."""

import argparse
import asyncio
import math
import random
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from calculo import Calculadora
from importar_showdown import normalizar_id

from .equipos import leer_equipo

FMT = "gen9championsvgc2026regmc"
EQ = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "final_frankfurt"
ARRANQUE = "En la carpeta pokemon-showdown ejecuta: node pokemon-showdown start --no-security {puerto}"


def url_websocket(url):
    """Admite SHOWDOWN_URL como base HTTP/WS o como endpoint websocket completo."""
    partes = urlsplit(url)
    esquema = {"http": "ws", "https": "wss", "ws": "ws", "wss": "wss"}.get(partes.scheme)
    if esquema is None or not partes.hostname:
        raise ValueError("SHOWDOWN_URL debe ser una URL http(s) o ws(s)")
    return urlunsplit((esquema, partes.netloc,
                       partes.path if partes.path not in ("", "/") else "/showdown/websocket",
                       partes.query, ""))


async def servidor_disponible(url, timeout=2):
    """Comprueba que el endpoint websocket responde antes de crear jugadores."""
    from websockets.asyncio.client import connect
    from websockets.exceptions import WebSocketException

    async def comprobar():
        async with connect(url_websocket(url), open_timeout=timeout, close_timeout=timeout) as conexion:
            async for mensaje in conexion:
                if "|challstr|" in mensaje:
                    return True
        return False

    try:
        return await asyncio.wait_for(comprobar(), timeout)
    except (OSError, asyncio.TimeoutError, WebSocketException):
        return False


def wilson(victorias, total):
    """Intervalo de Wilson del 95 % (z=1,95996398454), en fracciones."""
    if total <= 0 or not 0 <= victorias <= total:
        raise ValueError("Se necesita un total positivo y victorias entre 0 y total")
    z = 1.959963984540054
    p = victorias / total
    denominador = 1 + z * z / total
    centro = (p + z * z / (2 * total)) / denominador
    radio = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominador
    return max(0, centro - radio), min(1, centro + radio)


def validar_preview(preview, equipo, datos):
    """Cuatro especies diferentes del equipo, en orden: líderes y reservas."""
    if preview is None:
        return
    ids = [normalizar_id(e) for e in preview]
    disponibles = {normalizar_id(e) for e in leer_equipo(equipo, datos)}
    if len(ids) != 4 or len(set(ids)) != 4 or not set(ids) <= disponibles:
        raise ValueError("El preview debe contener cuatro especies distintas del equipo, separadas por comas")


def crear(tipo, equipo, rival, calc, nombre, preview=None, *, url="ws://localhost:8000", replays=None):
    from poke_env import AccountConfiguration, LocalhostServerConfiguration, ServerConfiguration
    from poke_env.player import RandomPlayer

    from .bot_reglas import BotReglas

    class Aleatorio(RandomPlayer):
        def teampreview(self, battle):
            if preview:
                miembros = list(battle.team.values())
                ids = [normalizar_id(m.species) for m in miembros]
                orden = [ids.index(normalizar_id(e)) + 1 for e in preview]
                for i in orden:
                    miembros[i - 1]._selected_in_teampreview = True
                return "/team " + "".join(map(str, orden))
            return self.random_teampreview(battle)

    cuenta = AccountConfiguration(f"{nombre}{uuid.uuid4().hex[:6]}", None)
    comun = dict(account_configuration=cuenta, battle_format=FMT,
                 server_configuration=ServerConfiguration(
                     url_websocket(url), LocalhostServerConfiguration.authentication_url),
                 max_concurrent_battles=10, save_replays=str(replays) if replays else False)
    if tipo == "aleatorio":
        return Aleatorio(team=equipo, **comun)
    if tipo not in ("reglas", "dano"):
        raise ValueError("Tipo de bot desconocido: " + tipo)
    opciones = {"solo_dano": True, "temperatura": 0} if tipo == "dano" else {}
    return BotReglas(equipo_propio=equipo, equipo_rival=rival, calculadora=calc,
                     preview=preview, **opciones, **comun)


async def serie(tipo_a, tipo_b, eq_a, eq_b, n, calc, *, preview_a=None, preview_b=None,
                seed=0, puerto=8000, url=None, replays=None):
    """A juega eq_a y B eq_b. Devuelve (victorias de A, partidas terminadas).

    seed fija la aleatoriedad Python de las decisiones de ambos bots. El
    servidor Showdown usa su propio RNG, por lo que no fija daño/precisión.
    Los replays se guardan desde la perspectiva de A, uno por partida.
    """
    if n <= 0:
        raise ValueError("El número de partidas debe ser positivo")
    validar_preview(preview_a, eq_a, calc.datos)
    validar_preview(preview_b, eq_b, calc.datos)
    url = url or f"ws://localhost:{puerto}"
    if not await servidor_disponible(url):
        raise ConnectionError(f"Showdown no responde en {url}. " + ARRANQUE.format(puerto=puerto))
    if replays:
        Path(replays).mkdir(parents=True, exist_ok=True)
    random.seed(seed)
    a = crear(tipo_a, eq_a, eq_b, calc, "A", preview_a, url=url, replays=replays)
    b = crear(tipo_b, eq_b, eq_a, calc, "B", preview_b, url=url)
    try:
        await a.battle_against(b, n_battles=n)
        return a.n_won_battles, a.n_finished_battles
    finally:
        await asyncio.gather(a.ps_client.stop_listening(), b.ps_client.stop_listening(),
                             return_exceptions=True)


def entero_positivo(texto):
    valor = int(texto)
    if valor <= 0:
        raise argparse.ArgumentTypeError("Debe ser un entero positivo")
    return valor


def preview_arg(texto):
    especies = [e.strip() for e in texto.split(",")]
    if len(especies) != 4 or any(not e for e in especies) or len({normalizar_id(e) for e in especies}) != 4:
        raise argparse.ArgumentTypeError("Indica cuatro especies distintas separadas por comas")
    return especies


def argumentos(argv=None):
    parser = argparse.ArgumentParser(description="Partidas de bots en Showdown Champions VGC (dobles)")
    parser.add_argument("--equipo-a", type=Path, default=EQ / "eric.txt")
    parser.add_argument("--equipo-b", type=Path, default=EQ / "sebastian.txt")
    parser.add_argument("--tipo-a", choices=("reglas", "dano", "aleatorio"), default="reglas")
    parser.add_argument("--tipo-b", choices=("reglas", "dano", "aleatorio"), default="reglas")
    parser.add_argument("--preview-a", type=preview_arg, help="4 especies: 2 líderes y 2 reservas")
    parser.add_argument("--preview-b", type=preview_arg, help="4 especies: 2 líderes y 2 reservas")
    parser.add_argument("--n", type=entero_positivo, default=200)
    parser.add_argument("--seed", type=int, default=0, help="Semilla de las decisiones Python (no del servidor)")
    parser.add_argument("--puerto", type=entero_positivo, default=8000)
    parser.add_argument("--replays", type=Path, help="Carpeta opcional para replays HTML de A")
    args = parser.parse_args(argv)
    if args.puerto > 65535:
        parser.error("El puerto debe estar entre 1 y 65535")
    return args


async def ejecutar(args):
    eq_a = args.equipo_a.read_text(encoding="utf-8")
    eq_b = args.equipo_b.read_text(encoding="utf-8")
    inicio = time.monotonic()
    url = f"ws://localhost:{args.puerto}"
    if not await servidor_disponible(url):
        raise ConnectionError(f"Showdown no responde en {url}. " + ARRANQUE.format(puerto=args.puerto))
    # Inicia Node antes de los jugadores: un fallo de instalación debe llegar
    # al CLI, no quedarse en una tarea de poke-env esperando una decisión.
    with Calculadora() as calc:
        ganadas, total = await serie(
            args.tipo_a, args.tipo_b, eq_a, eq_b, args.n, calc,
            preview_a=args.preview_a, preview_b=args.preview_b, seed=args.seed,
            puerto=args.puerto, replays=args.replays,
        )
    lo, hi = wilson(ganadas, total)
    print(f"A ({args.tipo_a}) vs B ({args.tipo_b}): A gana {ganadas}/{total} "
          f"({100 * ganadas / total:.1f} %); IC 95 % Wilson: "
          f"[{100 * lo:.1f} %, {100 * hi:.1f} %] en {time.monotonic() - inicio:.0f}s")


def main(argv=None):
    args = argumentos(argv)
    try:
        asyncio.run(ejecutar(args))
    except (OSError, ValueError, RuntimeError) as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
