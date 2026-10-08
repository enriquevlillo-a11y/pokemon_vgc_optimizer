import json

import pytest

import sets
from config import ruta_equipos_referencia, ruta_movimientos, ruta_nombres
from exportar import a_showdown


@pytest.fixture
def catalogo():
    return {
        "protect": {"categoria": "Status", "potencia": 0},
        "stabfuerte": {"categoria": "Physical", "tipo": "Grass", "potencia": 90},
        "stabdebil": {"categoria": "Physical", "tipo": "Grass", "potencia": 40},
        "cobertura": {"categoria": "Physical", "tipo": "Normal", "potencia": 150},
        "otro": {"categoria": "Physical", "tipo": "Normal", "potencia": 80},
        "especial": {"categoria": "Special", "tipo": "Grass", "potencia": 160},
        "variable": {"categoria": "Physical", "tipo": "Grass", "potencia": 0},
        "status": {"categoria": "Status", "tipo": "Grass", "potencia": 200},
        "noaprendido": {"categoria": "Physical", "tipo": "Grass", "potencia": 200},
    }


@pytest.fixture
def especie(catalogo):
    return {"prueba": {
        "stats": {"attack": 100, "special-attack": 100}, "tipos": ["grass"],
        "habilidades": [{"nombre": "leaf-guard"}, {"nombre": "queenly-majesty"}],
        "movimientos": [m for m in catalogo if m != "noaprendido"] + ["sincatalogo"],
    }}


def test_generico_fisico_empate_stab_y_potencia(especie, catalogo):
    entrada = sets.set_generico("prueba", especie, catalogo)
    assert entrada["generico"] is True
    assert entrada["habilidad"] == "leafguard"
    assert entrada["objeto"] is None
    assert entrada["orientacion"] == "fisica"
    assert entrada["naturaleza"] == "Adamant"
    assert entrada["puntos"] == {"hp": 2, "attack": 32, "defense": 0,
                                "special-attack": 0, "special-defense": 0, "speed": 32}
    assert entrada["movimientos"] == ["protect", "stabfuerte", "stabdebil", "cobertura"]


def test_generico_especial_sin_protect(especie, catalogo):
    especie["prueba"]["stats"]["special-attack"] = 101
    especie["prueba"]["movimientos"].remove("protect")
    especie["prueba"]["habilidades"] = ["keen-eye", "infiltrator"]
    entrada = sets.set_generico("prueba", especie, catalogo)
    assert entrada["habilidad"] == "keeneye"
    assert entrada["orientacion"] == "especial"
    assert entrada["naturaleza"] == "Modest"
    assert entrada["puntos"]["special-attack"] == 32
    assert entrada["puntos"]["attack"] == 0
    assert sum(entrada["puntos"].values()) == 66
    assert entrada["movimientos"] == ["especial"]


@pytest.mark.parametrize("uso", [None, {}, {"pokemon": {}}, {"pokemon": {"prueba": {}}}])
def test_equipo_sin_uso_conserva_miembros(especie, catalogo, uso):
    resultado = sets.sets_equipo(["prueba"], uso, especie, catalogo)
    assert len(resultado) == 1
    assert resultado[0]["generico"] is True


@pytest.mark.parametrize("reparto,mensaje", [
    ("2/33/0/0/0/31", "attack tiene 33.*entre 0 y 32"),
    ("3/32/0/0/0/32", "total 67.*máximo es 66"),
])
def test_probable_rechaza_puntos_excesivos(reparto, mensaje):
    uso = {"prueba": {"spreads": {"Adamant:" + reparto: 100}}}
    with pytest.raises(ValueError, match="prueba.*" + mensaje):
        sets.set_probable("prueba", uso, {}, movimientos={})


@pytest.mark.parametrize("jugador,generico,orientacion,naturaleza", [
    ("Yvar Vlieger", "meowstic", "especial", "Modest"),
    ("Emilio Forbes", "tsareena", "fisica", "Adamant"),
])
def test_referencias_exportan_seis(datos, uso_smogon, jugador, generico, orientacion, naturaleza):
    referencias = json.loads(ruta_equipos_referencia().read_text(encoding="utf-8"))
    referencia = next(r for r in referencias if jugador in r["nombre"])
    movimientos = json.loads(ruta_movimientos().read_text(encoding="utf-8"))
    nombres = json.loads(ruta_nombres().read_text(encoding="utf-8"))
    resultado = sets.sets_equipo(referencia["equipo"], uso_smogon, datos, movimientos)
    assert [s["nombre"] for s in resultado] == referencia["equipo"]
    entrada = next(s for s in resultado if s["nombre"] == generico)
    assert entrada["generico"] is True
    assert entrada["orientacion"] == orientacion
    assert entrada["naturaleza"] == naturaleza
    assert len(entrada["movimientos"]) == 4
    assert entrada["movimientos"][0] == "protect"
    assert set(entrada["movimientos"]) <= set(datos[generico]["movimientos"])
    assert a_showdown(resultado, datos, nombres).count("Level: 50") == 6


def test_todos_los_sets_respetan_limites(datos, uso_smogon):
    referencias = json.loads(ruta_equipos_referencia().read_text(encoding="utf-8"))
    for referencia in referencias:
        resultado = sets.sets_equipo(referencia["equipo"], uso_smogon, datos)
        assert len(resultado) == 6, referencia["nombre"]
        for entrada in resultado:
            assert all(0 <= p <= 32 for p in entrada["puntos"].values()), entrada["nombre"]
            assert sum(entrada["puntos"].values()) <= 66, entrada["nombre"]
