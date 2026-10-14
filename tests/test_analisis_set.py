"""Propiedades de cortes, lotes de daño y edición de sets en Streamlit."""

from copy import deepcopy
from contextlib import nullcontext
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import analisis_set
from analisis_set import calculos_clave, puntos_para_superar, velocidad_set, velocidades_relevantes
from calculo import Calculadora, DIRECTORIO_CALCULO, set_a_calculo
from sets import set_probable


@pytest.fixture
def sinteticos():
    datos = {n: {"stats": {"speed": 100}, "tipos": ["normal"]} for n in ("propio", "rival")}
    entrada = {"nombre": "propio", "naturaleza": "Modest", "puntos": {"speed": 10}}
    uso = {"pokemon": {"rival": {"uso": 100, "spreads": {"Modest:0/0/0/0/0/5": 100}}}}
    return entrada, datos, uso


def test_velocidad_conocida_y_piedra(datos):
    entrada = {"nombre": "garchomp-mega-z", "naturaleza": "Modest", "puntos": {"speed": 32}}
    assert velocidad_set(entrada, datos) == 203
    assert velocidad_set({**entrada, "nombre": "garchomp", "objeto": "garchompitez"}, datos) == 203


@pytest.mark.parametrize("objetivo,opciones,esperado", [
    (125, {}, -4), (130, {}, 1), (151, {}, 22), (152, {}, None),
    (240, {"tailwind": True}, -9), (260, {"tailwind": True}, 1),
    (304, {"tailwind": True}, None),
    (130, {"trick_room": True}, -1), (153, {"trick_room": True}, 22),
    (120, {"trick_room": True}, None),
])
def test_puntos_para_superar_sinteticos(sinteticos, objetivo, opciones, esperado):
    entrada, datos, _ = sinteticos
    original = deepcopy(entrada)
    assert puntos_para_superar(entrada, datos, objetivo, **opciones) == esperado
    assert entrada == original


@pytest.mark.parametrize("naturaleza", ["Modest", "Timid", "Quiet"])
@pytest.mark.parametrize("objeto", [None, "choicescarf"])
def test_corte_es_estricto_y_minimo_con_truncamientos(sinteticos, naturaleza, objeto):
    entrada, datos, _ = sinteticos
    entrada.update(naturaleza=naturaleza, objeto=objeto)
    for objetivo in range(80, 260):
        delta = puntos_para_superar(entrada, datos, objetivo)
        if delta is None:
            assert velocidad_set(entrada, datos, puntos=32) <= objetivo
        else:
            puntos = entrada["puntos"]["speed"] + delta
            assert velocidad_set(entrada, datos, puntos=puntos) > objetivo
            if puntos:
                assert velocidad_set(entrada, datos, puntos=puntos - 1) <= objetivo


def test_tabla_velocidad_empates_tailwind_trick_room_y_sin_spread(sinteticos):
    entrada, datos, uso = sinteticos
    fila = velocidades_relevantes(entrada, datos, uso, n=1)[0]
    assert fila["velocidad"] == 125
    assert fila["comparacion"] == fila["comparacion_tailwind"] == "más rápido"
    assert fila["comparacion_trick_room"] == "más lento"
    assert fila["puntos_spe"] == -4
    entrada["puntos"]["speed"] = 5
    fila = velocidades_relevantes(entrada, datos, uso)[0]
    assert fila["comparacion"] == fila["comparacion_trick_room"] == "empate"
    uso["pokemon"]["rival"]["spreads"] = {}
    fila = velocidades_relevantes(entrada, datos, uso)[0]
    assert fila["velocidad"] is fila["puntos_spe"] is None
    assert fila["comparacion"] == "sin datos"
    assert velocidades_relevantes(entrada, datos, {}, n=20) == []
    assert velocidades_relevantes(entrada, datos, uso, n=0) == []


def test_amenaza_usa_spread_mas_comun_de_su_variante(datos, uso_smogon):
    from datos_uso import seleccionar_variante
    from velocidad import velocidades_reales

    entrada = {"nombre": "gholdengo", "naturaleza": "Timid", "puntos": {"speed": 32}}
    filas = velocidades_relevantes(entrada, datos, uso_smogon)
    assert len(filas) == 20
    assert [f["uso"] for f in filas] == sorted((f["uso"] for f in filas), reverse=True)
    for fila in filas:
        variante = seleccionar_variante(fila["nombre"], uso_smogon)
        assert fila["velocidad"] == velocidades_reales(fila["nombre"], uso_smogon, datos, variante)[fila["forma"]]


@pytest.fixture
def duelo(datos):
    entrada = {"nombre": "garchomp", "naturaleza": "Modest", "objeto": "garchompitez",
               "habilidad": "roughskin", "puntos": {"hp": 2, "special-attack": 32, "speed": 32},
               "movimientos": ["earthpower", "dracometeor", "flamethrower", "protect"]}
    uso = {"pokemon": {"torkoal": {"uso": 100, "habilidades": {"drought": 100},
                                  "spreads": {"Quiet:0/0/0/32/0/0": 100},
                                  "movimientos": {"eruption": 90, "flamethrower": 80, "protect": 70}}}}
    return entrada, uso


def test_dano_una_llamada_y_errores_no_son_ceros(monkeypatch, datos, duelo):
    entrada, uso = duelo
    llamadas = []

    class FalsaCalculadora:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def calcular_lote(self, peticiones):
            llamadas.append(peticiones)
            return [{"ok": False, "error": "ataque inválido"} for _ in peticiones]

    monkeypatch.setattr(analisis_set, "Calculadora", FalsaCalculadora)
    fila = calculos_clave(entrada, datos, uso)[0]
    assert len(llamadas) == 1
    assert len(llamadas[0]) == len(entrada["movimientos"]) + len(set_probable("torkoal", uso, datos)["movimientos"])
    assert llamadas[0][0]["atacante"]["especie"] == "Garchomp-Mega-Z"
    assert fila["ataque"] is fila["defensa"] is None
    assert len(fila["errores"]) == len(llamadas[0])
    assert fila["ventaja"] == "neutra"


@pytest.mark.parametrize("ko_propio,ko_rival,ventaja", [
    ("guaranteed OHKO", "guaranteed 3HKO", "favorable"),
    ("guaranteed 3HKO", "guaranteed 2HKO after Leftovers recovery", "desfavorable"),
    ("guaranteed 2HKO", "guaranteed OHKO", "neutra"),
    ("50% chance to OHKO", "guaranteed 3HKO", "neutra"),
])
def test_ventaja_exige_ko_corto_garantizado_en_un_solo_sentido(monkeypatch, datos, duelo,
                                                           ko_propio, ko_rival, ventaja):
    entrada, uso = duelo

    def calcular(peticiones):
        return [{"ok": True, "min": 1, "max": 2,
                 "ko": ko_propio if p["atacante"]["especie"] == "Garchomp-Mega-Z" else ko_rival}
                for p in peticiones]

    monkeypatch.setattr(analisis_set, "Calculadora", lambda **kwargs: nullcontext(
        SimpleNamespace(calcular_lote=calcular)))
    assert calculos_clave(entrada, datos, uso)[0]["ventaja"] == ventaja


requiere_calculadora = pytest.mark.skipif(
    not shutil.which("node") or not (DIRECTORIO_CALCULO / "node_modules" / "@smogon" / "calc" / "package.json").is_file(),
    reason="Se necesita Node y npm ci --prefix calculo",
)


@requiere_calculadora
def test_mejores_ataques_y_ohko_por_propiedades(monkeypatch, datos, duelo):
    entrada, uso = duelo
    original = deepcopy(entrada)
    llamadas = []
    calcular_original = Calculadora.calcular_lote

    def registrar(self, peticiones):
        llamadas.append(len(peticiones))
        return calcular_original(self, peticiones)

    with monkeypatch.context() as m:
        m.setattr(Calculadora, "calcular_lote", registrar)
        fila = calculos_clave(entrada, datos, uso)[0]
    assert len(llamadas) == 1
    assert not fila["errores"]
    assert entrada == original
    with Calculadora() as calc:
        propia = set_a_calculo(entrada, datos, calc.nombres, megaevolucionado=True)
        rival = set_a_calculo(set_probable("torkoal", uso, datos), datos, calc.nombres, megaevolucionado=True)
        for lado, a, d in (("ataque", propia, rival), ("defensa", rival, propia)):
            respuestas = calc.calcular_lote([{"atacante": a, "defensor": d, "movimiento": mov}
                                             for mov in a["movimientos"]])
            assert all(r["ok"] for r in respuestas)
            mejor = max(respuestas, key=lambda r: (r["max"], r["min"]))
            assert (fila[lado]["min"], fila[lado]["max"]) == (mejor["min"], mejor["max"])
            assert fila[lado]["porcentaje_min"] == pytest.approx(mejor["min"] * 100 / mejor["ps_defensor"])
            if mejor["min"] >= mejor["ps_defensor"]:
                assert fila[lado]["ko"] == "guaranteed OHKO"
        assert fila["ataque"]["min"] >= fila["ataque"]["ps_defensor"]


@requiere_calculadora
def test_inmunidades_son_dano_cero_y_no_errores(datos):
    entrada = {"nombre": "gholdengo", "naturaleza": "Timid", "habilidad": "goodasgold",
               "puntos": {"hp": 2, "special-attack": 32, "speed": 32},
               "movimientos": ["makeitrain", "shadowball", "protect"]}
    uso = {"pokemon": {"sneasler": {"uso": 100, "spreads": {"Jolly:2/32/0/0/0/32": 100},
                                  "movimientos": {"closecombat": 90, "direclaw": 80, "fakeout": 70}}}}
    fila = calculos_clave(entrada, datos, uso)[0]
    assert not fila["errores"]
    assert fila["defensa"]["min"] == fila["defensa"]["max"] == 0
    assert fila["defensa"]["ko"] == "sin daño"


@pytest.fixture
def app():
    st.cache_data.clear()
    try:
        yield AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run(timeout=30)
    finally:
        st.cache_data.clear()


def tabla_velocidad(app):
    return next(t.value for t in app.dataframe if "Tu velocidad" in t.value.columns)


def test_app_edita_naturaleza_cambia_velocidad_exporta_y_restablece(app):
    app.multiselect[0].set_value(["gholdengo"]).run(timeout=30)
    assert not app.exception
    antes = tabla_velocidad(app).copy()
    naturaleza = next(s for s in app.selectbox if s.label == "Naturaleza")
    inicial = naturaleza.value
    nueva = "Quiet" if inicial != "Quiet" else "Timid"
    naturaleza.set_value(nueva).run(timeout=30)
    assert not app.exception
    despues = tabla_velocidad(app)
    assert antes["Tu velocidad"].iloc[0] != despues["Tu velocidad"].iloc[0]
    assert f"{nueva} Nature" in app.code[0].value
    assert next(iter(app.session_state["sets_editados"].values()))["naturaleza"] == nueva
    app.multiselect[0].set_value([]).run(timeout=30)
    app.multiselect[0].set_value(["gholdengo"]).run(timeout=30)
    assert not app.exception
    assert f"{nueva} Nature" in app.code[0].value
    next(b for b in app.button if b.label == "Volver al set probable").click().run(timeout=30)
    assert not app.exception
    assert tabla_velocidad(app).equals(antes)
    assert f"{inicial} Nature" in app.code[0].value


@pytest.mark.parametrize("falta", ["node", "modulos"])
def test_app_avisa_puntos_y_sigue_sin_dependencias(app, monkeypatch, tmp_path, falta):
    if falta == "node":
        monkeypatch.setattr(shutil, "which", lambda _: None)
    else:
        import calculo
        monkeypatch.setattr(calculo, "DIRECTORIO_CALCULO", tmp_path)
    app.multiselect[0].set_value(["gholdengo"]).run(timeout=30)
    assert not app.exception
    assert any("npm ci --prefix calculo" in w.value for w in app.warning)
    for numero in app.number_input:
        numero.set_value(32)
    app.run(timeout=30)
    assert not app.exception
    assert any("Sobran" in w.value for w in app.warning)
    assert len(tabla_velocidad(app)) == 20
    assert len(app.get("download_button")) == 0
    assert len(app.code) == 0
