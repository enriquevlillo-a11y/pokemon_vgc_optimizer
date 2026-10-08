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
