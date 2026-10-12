"""Lógica C1b sin servidor e integración opcional con Showdown Champions."""

import asyncio
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest

from bots import combinar, leer_equipo, valor_golpe, valorar_control_velocidad, velocidad_efectiva
from bots.experimento import EQ, argumentos, main, serie, servidor_disponible, validar_preview, wilson
from calculo import BASE, DIRECTORIO_CALCULO, Calculadora, set_a_calculo


@pytest.mark.parametrize("rango,ps,precision,esperado", [
    ((0.8, 1.0), 0.7, 1, 1.3),  # KO seguro: PS restantes + bonus
    ((0.2, 0.4), 0.8, 1, 0.3),  # KO imposible
    ((0.4, 0.8), 0.6, 1, 0.9),  # KO parcial: probabilidad 1/2
    ((0.4, 0.8), 0.6, 0.75, 0.675),
    ((0.6, 0.6), 0.6, 1, 1.2),  # rango constante en el umbral
    ((0.2, 0.4), 0.8, 0, 0),
])
def test_valor_golpe(rango, ps, precision, esperado):
    assert valor_golpe(rango, ps, precision) == pytest.approx(esperado)


def test_combinar_ko_conjunto_y_objetivos_distintos():
    golpe = {"rival": ((0.4, 0.5), 0.8, 1)}
    assert valor_golpe((0.4, 0.5), 0.8) < 0.8
    assert combinar(golpe, golpe) == pytest.approx(1.4)
    assert combinar(golpe, {"otro": ((0.4, 0.5), 0.8, 1)}) == pytest.approx(0.9)
    assert combinar({}, {}) == 0
    # La precisión pondera los rangos antes de calcular el KO conjunto.
    assert combinar(golpe, {"rival": ((0.4, 0.5), 0.8, 0.5)}) == pytest.approx(0.675)


@pytest.mark.parametrize("movimiento,propias,rivales,opciones,esperado", [
    ("trickroom", [40, 60], [100, 120], {}, 0.6),
    ("trickroom", [100, 120], [40, 60], {}, -0.6),
    ("trickroom", [40, 110], [100, 120], {}, 0.3),
    ("trickroom", [40, 60], [100, 120], {"trick_room": True}, 0),
    ("trickroom", [100, 120], [40, 60], {"trick_room": True}, 0),
    ("trickroom", [100, 100], [100, 100], {}, 0),
    ("trickroom", [], [100, 120], {}, 0),
    ("tailwind", [40, 60], [100, 120], {}, 0.55),
    ("tailwind", [100, 120], [40, 60], {}, 0),
    ("tailwind", [40, 110], [100, 120], {}, 0.275),
    ("tailwind", [40, 60], [100, 120], {"tailwind": True}, 0),
    ("tailwind", [40, 60], [100, 120], {"trick_room": True}, 0),
    ("tailwind", [100, 100], [100, 100], {}, 0),
    ("tailwind", [100, 120], [], {}, 0),
])
def test_control_velocidad(movimiento, propias, rivales, opciones, esperado):
    assert valorar_control_velocidad(movimiento, propias, rivales, **opciones) == pytest.approx(esperado)


@pytest.mark.parametrize("stat,boost,opciones,esperado", [
    (100, 0, {}, 100), (100, 1, {}, 150), (100, -1, {}, 66),
    (100, 6, {}, 400), (100, -6, {}, 25),
    (101, 0, {"scarf": True}, 151),
    (100, 0, {"tailwind": True}, 200),
    (101, 0, {"paralizado": True}, 50),
    (101, 1, {"scarf": True, "tailwind": True, "paralizado": True}, 226),
    (1, -6, {"paralizado": True}, 1),
])
def test_velocidad_efectiva(stat, boost, opciones, esperado):
    assert velocidad_efectiva(stat, boost, **opciones) == esperado


def test_modificadores_cambian_la_valoracion():
    lento = velocidad_efectiva(100)
    rapido = velocidad_efectiva(100, scarf=True)
    assert valorar_control_velocidad("trickroom", [lento], [120]) > 0
    assert valorar_control_velocidad("trickroom", [rapido], [120]) < 0
    paralizado = velocidad_efectiva(rapido, paralizado=True)
    assert valorar_control_velocidad("tailwind", [paralizado], [120]) > 0


@pytest.mark.parametrize("archivo,especies", [
    ("eric.txt", ["raichu", "garchomp", "incineroar", "volcarona", "rillaboom", "gholdengo"]),
    ("sebastian.txt", ["garchomp", "incineroar", "farigiraf", "sneasler", "torkoal", "sylveon"]),
])
def test_leer_equipos_final(datos, archivo, especies):
    equipo = leer_equipo((EQ / archivo).read_text(encoding="utf-8"), datos)
    assert list(equipo) == especies
    assert all(len(e["movimientos"]) == 4 and sum(e["puntos"].values()) == 66
               for e in equipo.values())
    assert equipo["garchomp"]["objeto"] == "Garchompite Z"
    assert equipo["garchomp"]["habilidad"] == "Rough Skin"
    assert equipo["garchomp"]["naturaleza"] == "Modest"
    assert equipo["garchomp"]["puntos"] == {"hp": 2, "special-attack": 32, "speed": 32}
    movimiento = "Earth Power" if archivo == "eric.txt" else "Draco Meteor"
    assert movimiento in equipo["garchomp"]["movimientos"]


def test_leer_equipo_crlf_apodo_y_vacio(datos):
    texto = "Amigo (Incineroar) (M) @ Sitrus Berry\r\nAbility: Intimidate\r\n- Fake Out\r\n  \r\nTorkoal\r\n- Protect\r\n"
    equipo = leer_equipo(texto, datos)
    assert list(equipo) == ["incineroar", "torkoal"]
    assert equipo["incineroar"]["objeto"] == "Sitrus Berry"
    assert equipo["torkoal"]["movimientos"] == ["Protect"]
    assert leer_equipo(" \n", datos) == {}


def test_utilidades_sin_poke_env():
    codigo = """
import builtins
original = builtins.__import__
def sin_poke_env(nombre, *args, **kwargs):
    if nombre.startswith('poke_env'):
        raise ImportError('poke-env no instalado')
    return original(nombre, *args, **kwargs)
builtins.__import__ = sin_poke_env
from bots import leer_equipo, valor_golpe, combinar, valorar_control_velocidad
assert leer_equipo('', {}) == {}
assert valor_golpe((1, 1), 1) == 1.6
assert combinar({}, {}) == 0
assert valorar_control_velocidad('trickroom', [40], [100]) == 0.6
"""
    resultado = subprocess.run([sys.executable, "-c", codigo], cwd=BASE,
                               capture_output=True, text=True, timeout=10)
    assert resultado.returncode == 0, resultado.stderr


def test_velocidades_del_bot_usan_sets_y_estado(datos):
    pytest.importorskip("poke_env")
    from bots.bot_reglas import BotReglas
    from poke_env.battle import Field, SideCondition, Status

    bot = BotReglas.__new__(BotReglas)
    bot.calc = Calculadora(datos=datos)
    set_base = {"nombre": "garchomp", "naturaleza": "Modest", "puntos": {"speed": 32},
                "objeto": "Choice Scarf"}
    normal = set_a_calculo(set_base, datos, bot.calc.nombres)
    mega = set_a_calculo({**set_base, "nombre": "garchomp-mega-z"}, datos, bot.calc.nombres)
    bot.sets = {("propio", "garchomp"): (normal, mega), ("rival", "garchomp"): (normal, mega)}
    propio = SimpleNamespace(species="garchompmegaz", fainted=False, boosts={"spe": 1},
                             status=Status.PAR, item="unknown_item")
    rival = SimpleNamespace(species="garchomp", fainted=False, boosts={}, status=None, item=None)
    # Mega-Z: 203 naturales, +1 => 304, Scarf => 456, TW y PAR se cancelan.
    assert bot._velocidades([propio, None], "propio", True) == [456]
    propio.item = None  # Scarf retirado; no se recupera del set abierto.
    assert bot._velocidades([propio], "propio", True) == [304]
    assert bot._velocidades([rival], "rival", False) == [154]
    propio.boosts = {}
    batalla = SimpleNamespace(active_pokemon=[propio, None], opponent_active_pokemon=[rival, None],
                              side_conditions={}, opponent_side_conditions={}, fields={})
    assert bot._control_velocidad(batalla, "trickroom") == 0.6
    propio.status = None
    assert bot._control_velocidad(batalla, "trickroom") == -0.6
    batalla.opponent_side_conditions = {SideCondition.TAILWIND: 1}
    assert bot._control_velocidad(batalla, "tailwind") == 0.55
    batalla.fields = {Field.TRICK_ROOM: 1}
    assert bot._control_velocidad(batalla, "trickroom") == 0
    propio.fainted = True
    assert bot._velocidades([propio], "propio", False) == []


def test_cli_argumentos_y_preview(datos, tmp_path):
    args = argumentos(["--equipo-a", "a.txt", "--equipo-b", "b.txt", "--tipo-a", "dano",
                       "--tipo-b", "aleatorio", "--n", "10", "--seed", "42", "--puerto", "9000",
                       "--preview-a", "volcarona,garchomp,gholdengo,incineroar", "--replays", str(tmp_path)])
    assert (args.equipo_a, args.equipo_b) == (Path("a.txt"), Path("b.txt"))
    assert (args.tipo_a, args.tipo_b, args.n, args.seed, args.puerto) == ("dano", "aleatorio", 10, 42, 9000)
    assert args.replays == tmp_path
    equipo = (EQ / "eric.txt").read_text(encoding="utf-8")
    validar_preview(args.preview_a, equipo, datos)
    with pytest.raises(ValueError, match="cuatro especies"):
        validar_preview(["torkoal", "garchomp", "gholdengo", "incineroar"], equipo, datos)


@pytest.mark.parametrize("argv", [["--n", "0"], ["--puerto", "65536"], ["--tipo-a", "otro"],
                                  ["--preview-a", "garchomp,garchomp,gholdengo,incineroar"]])
def test_cli_argumentos_invalidos(argv):
    with pytest.raises(SystemExit) as error:
        argumentos(argv)
    assert error.value.code == 2


def test_wilson():
    assert wilson(5, 10) == pytest.approx((0.2365930905, 0.7634069095))
    assert wilson(0, 10) == pytest.approx((0, 0.2775327999))
    assert wilson(10, 10) == pytest.approx((0.7224672001, 1))
    with pytest.raises(ValueError):
        wilson(0, 0)


def test_cli_sin_servidor_explica_arranque(monkeypatch):
    async def no_responde(_):
        return False
    monkeypatch.setattr("bots.experimento.servidor_disponible", no_responde)
    with pytest.raises(SystemExit, match="node pokemon-showdown start --no-security 9000"):
        main(["--puerto", "9000", "--n", "1"])


def test_sondeo_espera_challstr_tras_mensaje_inicial(monkeypatch):
    pytest.importorskip("websockets")

    class Conexion:
        def __init__(self):
            self.mensajes = iter(["|updateuser|Guest", "|challstr|4|reto"])

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        def __aiter__(self):
            return self

        async def __anext__(self):
            try:
                return next(self.mensajes)
            except StopIteration:
                raise StopAsyncIteration

    monkeypatch.setattr("websockets.asyncio.client.connect", lambda *args, **kwargs: Conexion())
    assert asyncio.run(servidor_disponible("ws://localhost:8000"))


def test_integracion_reglas_vs_aleatorio():
    if not shutil.which("node") or not (DIRECTORIO_CALCULO / "node_modules").is_dir():
        pytest.skip("Se necesita Node y npm ci --prefix calculo")
    pytest.importorskip("poke_env", reason="Se necesita poke-env==0.16.1")
    url = os.environ.get("SHOWDOWN_URL", "ws://localhost:8000")
    if not asyncio.run(servidor_disponible(url)):
        pytest.skip("Showdown no responde en localhost:8000 / SHOWDOWN_URL")

    async def partidas():
        with Calculadora() as calc:
            return await asyncio.wait_for(serie(
                "reglas", "aleatorio", (EQ / "eric.txt").read_text(encoding="utf-8"),
                (EQ / "sebastian.txt").read_text(encoding="utf-8"), 10, calc,
                seed=0, url=url,
            ), timeout=180)

    victorias, total = asyncio.run(partidas())
    assert total == 10
    assert victorias >= 8, f"Reglas ganó {victorias}/{total}; se esperaban al menos 8"


def test_trick_room_cuenta_la_reserva(datos):
    """Un líder rápido no debe anular Trick Room si la reserva es lenta."""
    pytest.importorskip("poke_env")
    from bots.bot_reglas import BotReglas

    bot = BotReglas.__new__(BotReglas)
    bot.calc = Calculadora(datos=datos)

    def par(nombre, naturaleza, velocidad):
        entrada = {"nombre": nombre, "naturaleza": naturaleza, "puntos": {"speed": velocidad}}
        s = set_a_calculo(entrada, datos, bot.calc.nombres)
        return s, s

    bot.sets = {("propio", "garchomp"): par("garchomp", "Jolly", 32),
                ("propio", "torkoal"): par("torkoal", "Quiet", 0),
                ("propio", "farigiraf"): par("farigiraf", "Quiet", 0),
                ("rival", "gholdengo"): par("gholdengo", "Timid", 32),
                ("rival", "volcarona"): par("volcarona", "Timid", 32)}
    mon = lambda especie: SimpleNamespace(species=especie, fainted=False, boosts={}, status=None, item=None)
    garchomp, torkoal, farigiraf = mon("garchomp"), mon("torkoal"), mon("farigiraf")
    gholdengo, volcarona = mon("gholdengo"), mon("volcarona")
    solo_activos = SimpleNamespace(active_pokemon=[garchomp, None], opponent_active_pokemon=[gholdengo, None],
                                   side_conditions={}, opponent_side_conditions={}, fields={})
    con_reserva = SimpleNamespace(**vars(solo_activos),
                                  team={"a": garchomp, "b": torkoal, "c": farigiraf},
                                  opponent_team={"x": gholdengo, "y": volcarona})
    # Activos: Garchomp (169) > Gholdengo (149) -> -0,6. Con la reserva lenta
    # (Torkoal, Farigiraf) el balance del equipo es positivo y el valor sube.
    assert bot._control_velocidad(solo_activos, "trickroom") == pytest.approx(-0.6)
    assert bot._control_velocidad(con_reserva, "trickroom") > bot._control_velocidad(solo_activos, "trickroom")
