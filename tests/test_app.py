from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest


def test_app_arranca_sin_errores(monkeypatch):
    import diagnostico

    explicar_original = diagnostico.explicar
    llamadas = []

    def explicar_visible(equipo, candidato, *args, **kwargs):
        llamadas.append(candidato)
        return explicar_original(equipo, candidato, *args, **kwargs)

    monkeypatch.setattr(diagnostico, "explicar", explicar_visible)
    ruta_app = Path(__file__).resolve().parent.parent / "app.py"
    app = AppTest.from_file(str(ruta_app)).run(timeout=30)

    assert not app.exception
    assert app.title[0].value == "Optimizador de equipos Pokémon VGC"

    app.button[0].click().run(timeout=30)

    assert not app.exception
    assert app.dataframe[0].value.iloc[0]["Pokémon"] == "incineroar"
    cabeceras = [cabecera.value for cabecera in app.header]
    assert "Amenazas del meta" in cabeceras
    assert cabeceras.index("Debilidades de tu equipo") < cabeceras.index("Recomendaciones")
    recomendaciones = app.dataframe[0].value
    assert "Por qué" in recomendaciones.columns
    assert recomendaciones["Por qué"].str.len().gt(0).all()
    assert llamadas == recomendaciones["Pokémon"].tolist()
    tabla_amenazas = app.dataframe[1].value
    assert len(tabla_amenazas) == 20
    prioridad = {"sin respuesta": 0, "en riesgo": 1, "cubierta": 2}
    estados = [prioridad[estado] for estado in tabla_amenazas["Estado"]]
    assert estados == sorted(estados)
    assert any("**Velocidad máxima:**" in texto.value for texto in app.markdown)
    assert any("**Velocidad real:**" in texto.value for texto in app.markdown)


def test_app_exporta_equipo_completo_con_fixtures(monkeypatch, tmp_path):
    import json
    import config
    import amenazas
    import streamlit as st

    from importar_showdown import extraer_movimientos

    fixtures = Path(__file__).parent / "fixtures"
    datos = json.loads(config.ruta_pokemon_datos().read_text())
    equipo = ["gholdengo", "volcarona", "garchomp", "incineroar", "rillaboom", "raichu"]
    for nombre in equipo:
        datos[nombre]["nombre_showdown"] = nombre.title()
    ruta_datos = tmp_path / "pokemon_datos.json"
    ruta_datos.write_text(json.dumps(datos))
    ruta_movimientos = tmp_path / "movimientos.json"
    ruta_movimientos.write_text(json.dumps(extraer_movimientos(
        fixtures / "moves.ts", fixtures / "champions-moves.ts")))
    monkeypatch.setattr(config, "ruta_pokemon_datos", lambda: ruta_datos)
    monkeypatch.setattr(config, "ruta_nombres", lambda: fixtures / "nombres_exportar.json")
    monkeypatch.setattr(config, "ruta_movimientos", lambda: ruta_movimientos)
    monkeypatch.setattr(amenazas, "ruta_movimientos", lambda: ruta_movimientos)
    st.cache_data.clear()
    try:
        app = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py")).run(timeout=30)
        app.multiselect[0].set_value(equipo).run(timeout=30)
        assert not app.exception
        assert "Incineroar @ Sitrus Berry" in app.code[0].value
        assert app.code[0].value.count("Level: 50") == 6
        assert len(app.get("download_button")) == 1
        amenazas = app.dataframe[1].value
        volcarona = amenazas[amenazas["Amenaza"] == "volcarona"].iloc[0]
        assert "garchomp (Rock Slide)" in volcarona["Con"]
    finally:
        st.cache_data.clear()


@pytest.mark.parametrize("jugador,generico", [
    ("Yvar Vlieger", "Meowstic"),
    ("Emilio Forbes", "Tsareena"),
])
def test_app_avisa_y_exporta_sets_genericos(jugador, generico):
    import json
    import streamlit as st

    from config import ruta_equipos_referencia

    referencias = json.loads(ruta_equipos_referencia().read_text(encoding="utf-8"))
    equipo = next(r["equipo"] for r in referencias if jugador in r["nombre"])
    st.cache_data.clear()
    try:
        app = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py")).run(timeout=30)
        app.multiselect[0].set_value(equipo).run(timeout=30)
        assert not app.exception
        assert f"{generico}: set genérico (sin datos de uso)" in [a.value for a in app.warning]
        assert app.code[0].value.count("Level: 50") == 6
        assert generico in app.code[0].value.splitlines()
        assert len(app.get("download_button")) == 1
    finally:
        st.cache_data.clear()
