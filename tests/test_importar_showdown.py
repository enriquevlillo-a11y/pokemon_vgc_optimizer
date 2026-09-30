from pathlib import Path

import pytest

pytest.importorskip("json5")

from importar_showdown import generar_datos, leer_typescript, normalizar_nombre


FIXTURES = Path(__file__).parent / "fixtures"


def cargar_fixture(nombre):
    return leer_typescript(FIXTURES / nombre)


def test_parsea_claves_numericas_de_habilidades():
    pokedex = cargar_fixture("pokedex.ts")

    assert pokedex["pikachu"]["abilities"] == {
        "0": "Static",
        "H": "Lightning Rod",
    }


def test_filtra_illegal_y_mythical():
    permitidos, _ = generar_datos(
        cargar_fixture("pokedex.ts"),
        cargar_fixture("formats-data.ts"),
        cargar_fixture("learnsets.ts"),
    )

    assert "missing-no" not in permitidos
    assert "mew" not in permitidos
    assert permitidos == ["pikachu", "salamence-mega"]


def test_mega_hereda_movimientos_de_especie_base():
    _, datos = generar_datos(
        cargar_fixture("pokedex.ts"),
        cargar_fixture("formats-data.ts"),
        cargar_fixture("learnsets.ts"),
    )

    mega = datos["salamence-mega"]
    assert mega["movimientos"] == ["dragonclaw", "protect"]
    assert mega["es_mega"] is True
    assert mega["objeto_mega"] == "Salamencite"


def test_normaliza_nombres_con_espacios_y_mayusculas():
    assert normalizar_nombre("Indeedee F") == "indeedee-f"
    assert normalizar_nombre("Salamence-Mega") == "salamence-mega"
