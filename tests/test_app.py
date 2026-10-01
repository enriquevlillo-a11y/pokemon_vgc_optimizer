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
