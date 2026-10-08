from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_app_arranca_sin_errores():
    ruta_app = Path(__file__).resolve().parent.parent / "app.py"
    app = AppTest.from_file(str(ruta_app)).run(timeout=30)

    assert not app.exception
    assert app.title[0].value == "Optimizador de equipos Pokémon VGC"

    app.button[0].click().run(timeout=30)

    assert not app.exception
    assert app.dataframe[0].value.iloc[0]["Pokémon"] == "incineroar"
    assert "Amenazas del meta" in [cabecera.value for cabecera in app.header]
    tabla_amenazas = app.dataframe[1].value
    assert len(tabla_amenazas) == 20
    assert tabla_amenazas.iloc[0]["Estado"] == "sin respuesta"
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
