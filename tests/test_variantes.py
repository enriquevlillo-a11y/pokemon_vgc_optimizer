import copy
import json
from pathlib import Path

import pytest

from amenazas import amenazas_del_meta, revisar_equipo
from datos_uso import entrada_variante, seleccionar_variante, uso_agregado
from exportar import a_showdown
from importar_uso_smogon import transformar_estadisticas
from puntuacion import puntuar
from recomendador import obtener_recomendaciones
from roles import roles_de
from sets import set_probable, sets_equipo
from velocidad import velocidad, velocidad_real, velocidades_reales


@pytest.fixture
def variantes():
    return json.loads((Path(__file__).parent / "fixtures" / "variantes_smogon.json").read_text())


def test_importador_conserva_formas_y_sus_porcentajes(variantes):
    resultado = transformar_estadisticas(variantes["estadisticas"], "2026-09", 1760, "fixture")
    assert resultado == variantes["uso"]
    garchomp = resultado["pokemon"]["garchomp"]
    assert garchomp["uso"] == 10
    assert garchomp["recuento"] == 1000
    assert garchomp["companeros"] == {"dragonite": 40}
    assert garchomp["megas"] == {"garchomp-mega-z": 10}
    normal, mega = (garchomp["variantes"][n] for n in ("garchomp", "garchomp-mega-z"))
    assert normal["uso"] == 3
    assert mega["uso"] == pytest.approx(7)
    assert normal["habilidades"] == {"roughskin": 90, "sandveil": 10}
    assert mega["habilidades"] == {"levitate": 100}
    assert normal["movimientos"]["dragonclaw"] == 95
    assert mega["movimientos"]["powergem"] == 95
    assert "powergem" not in normal["movimientos"]
    assert "dragonclaw" not in mega["movimientos"]
    assert mega["spreads"] == {"Modest:2/0/0/32/0/32": 100}


def test_importador_no_recorta_distribuciones_de_variantes(variantes):
    datos = variantes["estadisticas"]
    datos["data"]["Garchomp-Mega-Z"]["Moves"]["unused"] = 3
    resultado = transformar_estadisticas(datos, "2026-09", 1760)["pokemon"]["garchomp"]
    assert resultado["variantes"]["garchomp-mega-z"]["movimientos"]["unused"] == 1
    assert "unused" not in resultado["movimientos"]


@pytest.mark.parametrize("forma,naturaleza,objeto,ataques,habilidad", [
    ("garchomp", "Jolly", "lifeorb", {"dragonclaw", "earthquake"}, "roughskin"),
    ("garchomp-mega-z", "Modest", "garchompitez", {"powergem", "earthpower"}, "roughskin"),
    ("dragonite-mega", "Modest", "dragoninite", {"tailwind", "heatwave"}, "multiscale"),
])
def test_set_y_exportacion_usan_solo_la_forma(variantes, forma, naturaleza, objeto, ataques, habilidad):
    nombre = forma.split("-mega")[0]
    entrada = set_probable(nombre, variantes["uso"], variantes["datos"], variantes["movimientos"], forma)
    estadisticas = variantes["uso"]["pokemon"][nombre]["variantes"][forma]
    assert entrada["naturaleza"] == naturaleza
    assert entrada["objeto"] == objeto
    assert entrada["habilidad"] == habilidad
    assert ataques <= set(entrada["movimientos"]) <= set(estadisticas["movimientos"])
    if forma == "garchomp":
        assert entrada["objeto"] != "garchompitez"
        assert all(variantes["movimientos"][m]["categoria"] != "Special" for m in entrada["movimientos"])
    texto = a_showdown([entrada], variantes["datos"], variantes["nombres"])
    assert f"Ability: {variantes['nombres']['habilidades'][habilidad]}" in texto
    assert f"{naturaleza} Nature" in texto
    for ataque in ataques:
        assert f"- {variantes['nombres']['movimientos'][ataque]}" in texto
    assert f" @ {variantes['nombres']['objetos'][objeto]}" in texto


def test_por_defecto_gana_uso_y_no_raw_ni_spreads_agregados(variantes):
    uso, datos, movimientos = (variantes[k] for k in ("uso", "datos", "movimientos"))
    assert seleccionar_variante("garchomp", uso) == "garchomp-mega-z"
    assert set_probable("garchomp", uso, datos, movimientos)["naturaleza"] == "Modest"
    assert seleccionar_variante("dragonite", uso) == "dragonite"
    assert set_probable("dragonite", uso, datos, movimientos)["naturaleza"] == "Adamant"
    # La mayoría de Mega en recuento no sustituye la selección por uso de forma.
    assert uso["pokemon"]["dragonite"]["megas"]["dragonite-mega"] == 80


def test_roles_y_velocidad_de_la_variante(variantes):
    uso, datos = variantes["uso"], variantes["datos"]
    assert roles_de("dragonite", datos, uso, "dragonite-mega")["control_velocidad"]
    assert not roles_de("dragonite", datos, uso)["control_velocidad"]
    assert roles_de("dragonite", datos, uso, "dragonite")["anti_intimidate"]
    assert not roles_de("dragonite", datos, uso, "dragonite-mega")["anti_intimidate"]
    normal = velocidad("garchomp", datos, 32, 1.1)
    mega = velocidad("garchomp-mega-z", datos, 32, 1.0)
    assert velocidad_real("garchomp", uso, datos, "garchomp") == normal
    assert velocidad_real("garchomp", uso, datos) == mega
    assert velocidades_reales("garchomp", uso, datos) == {"garchomp": normal, "garchomp-mega-z": mega}
    assert velocidades_reales("garchomp", uso, datos, "garchomp") == {"garchomp": normal}


def test_amenazas_respetan_movimientos_tipos_habilidades_y_velocidad(variantes):
    uso, datos, movimientos = (variantes[k] for k in ("uso", "datos", "movimientos"))
    meta = {a["nombre"]: a for a in amenazas_del_meta(uso, datos=datos)}
    assert meta["garchomp"]["forma"] == "garchomp-mega-z"
    seleccion = {"garchomp": "garchomp"}
    meta = {a["nombre"]: a for a in amenazas_del_meta(uso, datos=datos, variantes=seleccion)}
    assert meta["garchomp"]["forma"] == "garchomp"
    def revisar(equipo, seleccion=None):
        return {a["nombre"]: a for a in revisar_equipo(equipo, datos, uso, movimientos=movimientos, variantes=seleccion)}
    mega = revisar(["garchomp"])
    normal = revisar(["garchomp"], seleccion)
    assert mega["volcarona"]["con"]["garchomp"] == ["Power Gem"]
    assert normal["volcarona"]["con"]["garchomp"] == ["Rock Slide"]
    datos["dragonite"]["stats"]["speed"] = 110
    assert "dragonite" in revisar(["dragonite"], seleccion)["garchomp"]["mas_rapidos"]
    assert "dragonite" not in revisar(["dragonite"])["garchomp"]["mas_rapidos"]
    # Heat Wave es cobertura de la Mega, aunque Dragonite no tenga tipo Fire.
    datos["garchomp"]["tipos"] = ["grass"]
    assert "garchomp" not in revisar(["garchomp"], seleccion)["dragonite"]["debiles"]
    assert "garchomp" in revisar(["garchomp"], {**seleccion, "dragonite": "dragonite-mega"})["dragonite"]["debiles"]
    # La Mega flota y solo es Dragon: el ataque Ground de Dragonite no la cubre.
    datos["garchomp-mega-z"]["tipos"] = ["electric"]
    assert "Earthquake" not in revisar(["dragonite"])["garchomp"]["con"].get("dragonite", [])
    uso["pokemon"]["garchomp"]["variantes"]["garchomp-mega-z"]["habilidades"] = {"roughskin": 100}
    assert "Earthquake" in revisar(["dragonite"])["garchomp"]["con"]["dragonite"]


def test_item_clause_no_usa_objetos_ni_ataques_de_otra_variante(variantes):
    uso, datos, movimientos = (variantes[k] for k in ("uso", "datos", "movimientos"))
    seleccion = {"garchomp": "garchomp", "dragonite": "dragonite"}
    resultado = sets_equipo(["dragonite", "garchomp"], uso, datos, movimientos, seleccion)
    dragonite, garchomp = resultado
    assert garchomp["objeto"] == "lifeorb"
    assert dragonite["objeto"] == "choicescarf"
    assert "protect" not in dragonite["movimientos"]
    assert "tailwind" not in dragonite["movimientos"]
    assert all(movimientos[m]["categoria"] != "Special" for m in dragonite["movimientos"])
    assert uso["pokemon"]["dragonite"]["variantes"]["dragonite"]["objetos"]["lifeorb"] == 70


def test_variante_erronea_no_mezcla_datos(variantes):
    with pytest.raises(ValueError, match="Variante desconocida"):
        set_probable("garchomp", variantes["uso"], variantes["datos"], variante="dragonite-mega")


def test_datos_antiguos_conservan_sets_roles_velocidad_y_amenazas(variantes):
    antiguo = uso_agregado(variantes["uso"])
    datos, movimientos = variantes["datos"], variantes["movimientos"]
    # El esquema histórico ignora la selección y conserva su comportamiento.
    for forma in (None, "garchomp", "garchomp-mega-z"):
        assert set_probable("garchomp", antiguo, datos, movimientos, forma) == set_probable("garchomp", antiguo, datos, movimientos)
        assert roles_de("garchomp", datos, antiguo, forma) == roles_de("garchomp", datos, antiguo)
        assert velocidad_real("garchomp", antiguo, datos, forma) == velocidad_real("garchomp", antiguo, datos)
    entrada = set_probable("garchomp", antiguo, datos, movimientos)
    assert entrada["naturaleza"] == "Jolly"
    assert entrada["objeto"] == "lifeorb"
    assert velocidad_real("garchomp", antiguo, datos) == velocidad("garchomp", datos, 32, 1.1)
    assert revisar_equipo(["garchomp"], datos, antiguo, movimientos=movimientos) == revisar_equipo(
        ["garchomp"], datos, antiguo, movimientos=movimientos, variantes={"garchomp": "garchomp-mega-z"})


def test_recomendador_y_puntuacion_siguen_usando_los_agregados(variantes):
    uso, datos = variantes["uso"], variantes["datos"]
    copia = copy.deepcopy(uso)
    agregado = uso_agregado(uso)
    for antisinergias in (True, False):
        assert obtener_recomendaciones(["dragonite"], datos, uso, antisinergias) == obtener_recomendaciones(["dragonite"], datos, agregado, antisinergias)
        assert puntuar([], "garchomp", datos, uso, antisinergias) == puntuar([], "garchomp", datos, agregado, antisinergias)
    assert uso == copia


def test_app_selector_actualiza_roles_amenazas_y_exportacion(variantes, monkeypatch, tmp_path):
    import config
    import amenazas
    import sets
    import streamlit as st
    from streamlit.testing.v1 import AppTest

    for clave, funcion in (("uso", "ruta_uso_smogon"), ("datos", "ruta_pokemon_datos"),
                          ("nombres", "ruta_nombres"), ("movimientos", "ruta_movimientos")):
        ruta = tmp_path / f"{clave}.json"
        ruta.write_text(json.dumps(variantes[clave]))
        monkeypatch.setattr(config, funcion, lambda ruta=ruta: ruta)
    monkeypatch.setattr(amenazas, "ruta_movimientos", config.ruta_movimientos)
    monkeypatch.setattr(sets, "ruta_movimientos", config.ruta_movimientos)
    st.cache_data.clear()
    try:
        app = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py")).run(timeout=30)
        app.multiselect[0].set_value(["garchomp", "dragonite"]).run(timeout=30)
        assert not app.exception
        assert app.selectbox(key="variante_garchomp").value == "garchomp-mega-z"
        assert app.selectbox(key="variante_dragonite").value == "dragonite"
        assert "Garchomp @ Garchompite Z" in app.code[0].value
        assert "- Power Gem" in app.code[0].value
        assert "control de velocidad" not in " ".join(m.value for m in app.markdown if "**Roles:**" in m.value)
        app.selectbox(key="variante_dragonite").set_value("dragonite-mega").run(timeout=30)
        assert not app.exception
        assert "Dragonite @ Dragoninite" in app.code[0].value
        assert "- Tailwind" in app.code[0].value
        assert "control de velocidad" in " ".join(m.value for m in app.markdown if "**Roles:**" in m.value)
        app.selectbox(key="variante_garchomp").set_value("garchomp").run(timeout=30)
        assert not app.exception
        assert "Garchompite Z" not in app.code[0].value
        assert "- Dragon Claw" in app.code[0].value
        volcarona = app.dataframe[1].value.query("Amenaza == 'volcarona'").iloc[0]
        assert "garchomp (Rock Slide)" in volcarona["Con"]
        assert "Power Gem" not in volcarona["Con"]
    finally:
        st.cache_data.clear()
