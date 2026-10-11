"""Referencias ejecutadas con @smogon/calc 0.12.0, Generations.get(0).

Eruption 258-306 usa Torkoal sin objeto; el fixture con Charcoal da 312-368.
"""

from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess
import sys
from time import perf_counter

import pytest

from calculo import BASE, DIRECTORIO_CALCULO, Calculadora, _leer_equipo, set_a_calculo
from velocidad import NATURALEZAS_LENTAS, NATURALEZAS_RAPIDAS, velocidad

pytestmark = pytest.mark.skipif(
    not shutil.which("node") or not (DIRECTORIO_CALCULO / "node_modules").is_dir(),
    reason="Se necesita node y npm ci --prefix calculo",
)

# Las referencias del punto 4 son sin objetos salvo la piedra de Garchomp.
# Los equipos de Frankfurt se prueban aparte, con todos sus objetos reales.
GARCHOMP = {"especie": "Garchomp-Mega-Z", "naturaleza": "Modest", "objeto": "Garchompite Z",
            "puntos": {"hp": 2, "spa": 32, "spe": 32}}
GHOLDENGO = {"especie": "Gholdengo", "naturaleza": "Timid", "puntos": {"hp": 17, "spa": 17, "spe": 32}}
TORKOAL = {"especie": "Torkoal", "naturaleza": "Quiet", "puntos": {"hp": 32, "spa": 32, "spd": 2}, "habilidad": "Drought"}


def peticion(atacante=GARCHOMP, defensor=GHOLDENGO, movimiento="Draco Meteor", **opciones):
    return {"atacante": deepcopy(atacante), "defensor": deepcopy(defensor), "movimiento": movimiento, **opciones}


@pytest.fixture
def calculadora():
    with Calculadora() as c:
        yield c


def test_stats_y_porcentajes(calculadora):
    r = calculadora.calcular(peticion())
    assert r["ok"]
    assert r["stats_atacante"]["spe"] == 203
    assert r["stats_atacante"]["hp"] == 185
    assert r["stats_defensor"]["spe"] == 149
    assert r["stats_defensor"]["hp"] == r["ps_defensor"] == 179
    assert r["porcentaje_min"] == pytest.approx(70 * 100 / 179)
    assert r["porcentaje_max"] == pytest.approx(83 * 100 / 179)
    assert r["ko"] == "guaranteed 3HKO"
    assert "70-83" in r["descripcion"]


@pytest.mark.parametrize("p,esperado", [
    (peticion(), (70, 83)),
    (peticion(defensor=TORKOAL, movimiento="Earth Power"), (158, 186)),
    (peticion(TORKOAL, GHOLDENGO, "Eruption", campo={"clima": "Sun"}), (258, 306)),
    (peticion({**TORKOAL, "objeto": "Charcoal"}, GHOLDENGO, "Eruption", campo={"clima": "Sun"}), (312, 368)),
    (peticion(TORKOAL, GHOLDENGO, "Eruption", campo={"clima": "Sun"}, isSpread=False), (344, 408)),
    (peticion({**TORKOAL, "ps_actuales": 88}, GHOLDENGO, "Eruption", campo={"clima": "Sun"}), (128, 152)),
    (peticion(campo={"helping_hand": True}), (105, 123)),
    (peticion(campo={"light_screen": True}), (47, 55)),
    (peticion(campo={"aurora_veil": True}), (47, 55)),
    (peticion(campo={"friend_guard": True}), (52, 62)),
    (peticion(campo={"terreno": "Misty"}), (35, 42)),
    (peticion(movimiento="Dragon Claw", campo={"reflect": True}), (18, 21)),
    (peticion({**GARCHOMP, "estado": "brn"}, movimiento="Dragon Claw"), (13, 16)),
    (peticion({**GARCHOMP, "boosts": {"spa": 1}}), (105, 123)),
])
def test_danos_de_la_biblioteca(calculadora, p, esperado):
    r = calculadora.calcular(p)
    assert r["ok"], r
    assert (r["min"], r["max"]) == esperado


@pytest.mark.parametrize("movimiento", ["Protect", "Seismic Toss"])
def test_sin_dano(calculadora, movimiento):
    r = calculadora.calcular(peticion(movimiento=movimiento))
    assert r["ok"]
    assert r["min"] == r["max"] == 0
    assert r["ko"] == "sin daño"


def test_ps_actuales_del_defensor_cambian_el_ko(calculadora):
    r = calculadora.calcular(peticion(defensor={**GHOLDENGO, "ps_actuales": 40}))
    assert r["ok"]
    assert (r["min"], r["max"]) == (70, 83)
    assert r["ps_defensor"] == 179
    assert r["ko"] == "guaranteed OHKO"


@pytest.mark.parametrize("nombre,naturaleza,puntos", [
    ("garchomp-mega-z", "Modest", 32), ("gholdengo", "Timid", 32),
    ("torkoal", "Quiet", 0), ("sneasler", "Adamant", 30),
    ("garchomp", "Jolly", 32), ("incineroar", "Sassy", 13),
    ("sylveon", "Modest", 0), ("gardevoir-mega", "Timid", 32),
])
def test_velocidad_coincide_con_python(calculadora, datos, nombre, naturaleza, puntos):
    a = {"especie": datos[nombre]["nombre_showdown"], "naturaleza": naturaleza, "puntos": {"speed": puntos}}
    r = calculadora.calcular(peticion(a, movimiento="Protect"))
    modificador = 1.1 if naturaleza in NATURALEZAS_RAPIDAS else 0.9 if naturaleza in NATURALEZAS_LENTAS else 1.0
    assert r["ok"], r
    assert r["stats_atacante"]["spe"] == velocidad(nombre, datos, puntos, modificador)


def test_conversion_y_mega(calculadora, datos):
    entrada = {"nombre": "garchomp", "objeto": "garchompitez", "habilidad": "roughskin",
               "naturaleza": "Modest", "puntos": {"hp": 2, "special-attack": 32, "speed": 32},
               "movimientos": ["earthpower", "protect"]}
    original = deepcopy(entrada)
    base = set_a_calculo(entrada, datos, calculadora.nombres)
    mega = set_a_calculo(entrada, datos, calculadora.nombres, megaevolucionado=True)
    assert base["especie"] == "Garchomp"
    assert base["habilidad"] == "Rough Skin"
    assert mega["especie"] == "Garchomp-Mega-Z"
    assert mega["habilidad"] == "Levitate"
    assert mega["objeto"] == "Garchompite Z"
    assert mega["movimientos"] == ["Earth Power", "Protect"]
    assert entrada == original
    explicita = set_a_calculo({**entrada, "nombre": "garchomp-mega-z"}, datos, calculadora.nombres)
    assert explicita == mega
    r = calculadora.calcular(peticion({**entrada, "megaevolucionado": True}, movimiento="dracometeor"))
    assert r["ok"] and (r["min"], r["max"]) == (70, 83)


@pytest.mark.parametrize("p,texto", [
    (peticion(movimiento="movimiento-inexistente"), "Movimiento inexistente"),
    (peticion({"especie": "pokemon-inexistente"}), "Especie inexistente"),
    (peticion({**GARCHOMP, "puntos": {"spa": 33}}), "Puntos inválidos"),
    (peticion({**GARCHOMP, "puntos": {"hp": 32, "spa": 32, "spe": 32}}), "máximo total"),
    (peticion(isSpread="false"), "isSpread"),
    (peticion({**GARCHOMP, "objeto": 123}), "Objeto"),
])
def test_valida_en_python_antes_de_enviar(calculadora, monkeypatch, p, texto):
    def prohibido(_):
        pytest.fail("Una petición inválida no debe enviarse a Node")
    with monkeypatch.context() as m:
        m.setattr(calculadora, "_enviar", prohibido)
        r = calculadora.calcular(p)
    assert not r["ok"] and texto in r["error"]
    assert calculadora.calcular(peticion())["ok"]


def test_servidor_recupera_errores_y_lotes(calculadora):
    proceso = calculadora._proceso
    pid = proceso.pid
    proceso.stdin.write("{json inválido\n")
    proceso.stdin.flush()
    r = json.loads(proceso.stdout.readline())
    assert not r["ok"] and "JSON inválido" in r["error"]
    respuestas = calculadora._enviar([
        peticion(movimiento="no existe"),
        peticion({"especie": "no existe"}),
        peticion({**GARCHOMP, "naturaleza": "no existe"}),
        peticion(campo={"clima": "no existe"}),
        peticion(),
    ])
    assert all(not r["ok"] for r in respuestas[:-1])
    assert "Movimiento inexistente" in respuestas[0]["error"]
    assert respuestas[-1]["ok"]
    assert calculadora.calcular(peticion())["ok"]
    assert proceso.pid == pid and proceso.poll() is None


def test_lote_mixto_preserva_orden_y_vacio(calculadora):
    respuestas = calculadora.calcular_lote([
        peticion(), peticion(movimiento="no existe"),
        peticion(movimiento="Protect"), peticion(defensor=TORKOAL, movimiento="Earth Power"),
    ])
    assert [r["ok"] for r in respuestas] == [True, False, True, True]
    assert [r["min"] for r in respuestas if r["ok"]] == [70, 0, 158]
    assert calculadora.calcular_lote([]) == []


def test_lote_1000_menos_de_cinco_segundos(calculadora):
    pid = calculadora._proceso.pid
    inicio = perf_counter()
    resultados = calculadora.calcular_lote([peticion()] * 1000)
    segundos = perf_counter() - inicio
    assert len(resultados) == 1000
    assert all(r["ok"] and (r["min"], r["max"]) == (70, 83) for r in resultados)
    assert segundos < 5, f"1000 cálculos tardaron {segundos:.3f} s"
    assert calculadora._proceso.pid == pid


def test_contexto_cierra_y_rutas_independientes_de_cwd(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    with Calculadora() as c:
        assert c.calcular(peticion())["ok"]
        proceso = c._proceso
    assert proceso.poll() is not None
    assert proceso.stdin.closed and proceso.stdout.closed
    c.cerrar()
    with pytest.raises(RuntimeError, match="cerrada"):
        c.calcular(peticion())


def test_instrucciones_si_faltan_dependencias(monkeypatch):
    with monkeypatch.context() as m:
        m.setattr(shutil, "which", lambda _: None)
        with pytest.raises(RuntimeError, match="npm ci --prefix calculo"):
            with Calculadora():
                pass
    with monkeypatch.context() as m:
        m.setattr(Path, "is_file", lambda _: False)
        with pytest.raises(RuntimeError, match="npm ci --prefix calculo"):
            with Calculadora():
                pass


def test_fixture_y_demostracion_frankfurt(calculadora):
    carpeta = BASE / "tests" / "fixtures" / "final_frankfurt"
    eric = _leer_equipo(carpeta / "eric.txt", calculadora.datos, calculadora.nombres)
    sebastian = _leer_equipo(carpeta / "sebastian.txt", calculadora.datos, calculadora.nombres)
    assert len(eric) == len(sebastian) == 6
    assert eric["garchomp"]["habilidad"] == "Levitate"
    respuestas = calculadora.calcular_lote([
        peticion(sebastian["torkoal"], eric["gholdengo"], "Eruption", campo={"clima": "Sun"}),
        peticion(sebastian["sylveon"], eric["garchomp"], "Hyper Voice"),
        peticion(eric["garchomp"], sebastian["torkoal"], "Earth Power"),
        peticion(eric["gholdengo"], sebastian["sylveon"], "Make It Rain"),
    ])
    assert all(r["ok"] for r in respuestas)
    assert [(r["min"], r["max"]) for r in respuestas] == [(312, 368), (186, 218), (158, 186), (151, 179)]
    demo = subprocess.run([sys.executable, str(BASE / "calculo.py")],
                          cwd=carpeta, capture_output=True, text=True, timeout=10)
    assert demo.returncode == 0, demo.stderr
    assert all(m in demo.stdout for m in ("Eruption", "Hyper Voice", "Earth Power", "Make It Rain"))
