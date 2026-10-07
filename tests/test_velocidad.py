import pytest

from velocidad import calcular_stat, velocidad, velocidad_real, velocidades_reales


@pytest.mark.parametrize("nombre,puntos,naturaleza,esperada", [
    ("garchomp", 32, 1.1, 169),
    ("garchomp", 0, 1.0, 122),
    ("sneasler", 30, 1.0, 170),
])
def test_formula_champions(datos, nombre, puntos, naturaleza, esperada):
    assert velocidad(nombre, datos, puntos, naturaleza) == esperada


def test_modificadores_truncan_scarf_antes_de_tailwind(datos):
    assert velocidad("garchomp", datos, scarf=True) == 253
    assert velocidad("garchomp", datos, tailwind=True) == 338
    assert velocidad("garchomp", datos, scarf=True, tailwind=True) == 506
    assert calcular_stat(108, 32, 0.9) == 144
    assert calcular_stat(108, 32, 1.1, ps=True) == 215


@pytest.mark.parametrize("puntos", [-1, 33, 1.5])
def test_puntos_invalidos(datos, puntos):
    with pytest.raises(ValueError, match="puntos"):
        velocidad("garchomp", datos, puntos=puntos)


def test_naturaleza_invalida(datos):
    with pytest.raises(ValueError, match="naturaleza"):
        velocidad("garchomp", datos, naturaleza=1.2)


@pytest.mark.parametrize("naturaleza,esperada", [
    ("Timid", 169), ("Jolly", 169), ("Hasty", 169), ("Naive", 169),
    ("Brave", 138), ("Quiet", 138), ("Relaxed", 138), ("Sassy", 138),
    ("Adamant", 154),
])
def test_real_elige_el_spread_mas_usado(datos, naturaleza, esperada):
    uso = {"pokemon": {"garchomp": {"spreads": {
        "Jolly:0/32/0/0/2/0": 1,
        f"{naturaleza}:0/32/0/0/2/32": 99,
    }}}}
    assert velocidad_real("garchomp", uso, datos) == esperada


@pytest.mark.parametrize("spreads", [{}, {"incorrecto": 100}, {"Jolly:0/32/0/0/2/33": 100}])
def test_real_sin_datos_validos(datos, spreads):
    assert velocidad_real("garchomp", {}, datos) is None
    assert velocidad_real("garchomp", {"garchomp": {"spreads": spreads}}, datos) is None


def test_velocidad_mega_comparte_spread_y_exige_mayoria(datos):
    entrada = {"spreads": {"Timid:2/0/0/32/0/32": 100}, "megas": {"gardevoir-mega": 50}}
    uso = {"gardevoir": entrada}
    assert velocidades_reales("gardevoir", uso, datos) == {"gardevoir": 145}
    entrada["megas"]["gardevoir-mega"] = 50.1
    assert velocidades_reales("gardevoir", uso, datos) == {"gardevoir": 145, "gardevoir-mega": 167}


def test_mega_suma_formas_y_elige_la_mas_usada(datos):
    uso = {"garchomp": {"spreads": {"Modest:2/0/0/32/0/32": 100},
                        "megas": {"garchomp-mega-z": 49, "garchomp-mega": 3}}}
    assert velocidades_reales("garchomp", uso, datos) == {"garchomp": 154, "garchomp-mega-z": 203}
