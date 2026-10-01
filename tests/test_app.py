import pytest

streamlit = pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest


def test_app_arranca_sin_errores():
    app = AppTest.from_file("app.py").run(timeout=30)

    assert not app.exception
    assert app.title[0].value == "Optimizador de equipos Pokémon VGC"
