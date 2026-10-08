import json
from pathlib import Path

import pytest

from amenazas import revisar_equipo
from config import ruta_pokemon_datos, ruta_uso_smogon, ruta_equipos_referencia
from evaluar import evaluar_referencias, resumir
from exportar import a_showdown
from importar_showdown import extraer_movimientos, extraer_nombres, generar_datos, leer_typescript
from sets import set_probable, sets_equipo

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def movimientos():
    return extraer_movimientos(FIXTURES / "moves.ts", FIXTURES / "champions-moves.ts")


@pytest.fixture
def datos():
    return json.loads(ruta_pokemon_datos().read_text())


@pytest.fixture
def uso():
    return json.loads(ruta_uso_smogon().read_text())


@pytest.fixture
def nombres():
    return json.loads((FIXTURES / "nombres_exportar.json").read_text())


def test_movimientos_y_override(movimientos):
    assert movimientos["rockslide"] == {
        "nombre": "Rock Slide", "tipo": "Rock", "categoria": "Physical",
        "potencia": 75, "prioridad": 0, "objetivo": "allAdjacentFoes",
    }
    assert movimientos["fakeout"]["potencia"] == 45
    assert movimientos["fakeout"]["nombre"] == "Fake Out"
    assert "secondary" not in movimientos
    assert extraer_nombres(FIXTURES / "abilities.ts")["intimidate"] == "Intimidate"


def test_nombre_original():
    _, datos = generar_datos(*(leer_typescript(FIXTURES / archivo) for archivo in
                              ("pokedex.ts", "formats-data.ts", "learnsets.ts")))
    assert datos["salamence-mega"]["nombre_showdown"] == "Salamence-Mega"


def test_eric_responde_volcarona(datos, uso, movimientos):
    equipo = ["gholdengo", "volcarona", "garchomp", "incineroar", "rillaboom", "raichu"]
    amenaza = next(a for a in revisar_equipo(equipo, datos, uso, movimientos=movimientos) if a["nombre"] == "volcarona")
    assert not amenaza["sin_respuesta"]
    assert "garchomp" in amenaza["le_pegan"]
    assert "Rock Slide" in amenaza["con"]["garchomp"]


def test_umbral_categoria_potencia_y_fallback(movimientos):
    datos = {"atacante": {"tipos": ["rock"], "stats": {"speed": 80}}, "volcarona": {"tipos": ["fire", "bug"], "stats": {"speed": 100}}}
    uso = {"pokemon": {"volcarona": {"uso": 10}, "atacante": {"movimientos": {"rockslide": 19.99}}}}
    assert revisar_equipo(["atacante"], datos, uso, movimientos=movimientos)[0]["sin_respuesta"]
    uso["pokemon"]["atacante"]["movimientos"]["rockslide"] = 20
    assert not revisar_equipo(["atacante"], datos, uso, movimientos=movimientos)[0]["sin_respuesta"]
    for campo, valor in [("categoria", "Status"), ("potencia", 0)]:
        modificados = {**movimientos, "rockslide": {**movimientos["rockslide"], campo: valor}}
        assert revisar_equipo(["atacante"], datos, uso, movimientos=modificados)[0]["sin_respuesta"]
    del uso["pokemon"]["atacante"]
    assert not revisar_equipo(["atacante"], datos, uso, movimientos={})[0]["sin_respuesta"]


def test_set_incineroar(datos, uso, nombres):
    entrada = set_probable("incineroar", uso, datos)
    assert nombres["habilidades"][entrada["habilidad"]] == "Intimidate"
    assert nombres["objetos"][entrada["objeto"]] == "Sitrus Berry"
    assert entrada["movimientos"][:2] == ["fakeout", "partingshot"]
    assert entrada["naturaleza"] == "Sassy"
    assert entrada["puntos"] == {"hp": 32, "attack": 0, "defense": 4,
                                "special-attack": 0, "special-defense": 30, "speed": 0}
    assert set_probable("desconocido", uso, datos) is None


def test_garchomp_mega(datos, uso, nombres):
    entrada = set_probable("garchomp", uso, datos)
    assert nombres["objetos"][entrada["objeto"]] == "Garchompite Z"


def test_mega_prioriza_piedra_sobre_objeto(datos):
    uso = {"pokemon": {"garchomp": {"megas": {"garchomp-mega-z": 51},
                                    "objetos": {"lifeorb": 90, "garchompitez": 10}}}}
    assert set_probable("garchomp", uso, datos)["objeto"] == "garchompitez"
    uso["pokemon"]["garchomp"]["megas"]["garchomp-mega-z"] = 50
    assert set_probable("garchomp", uso, datos)["objeto"] == "lifeorb"


def test_item_clause():
    uso = {"pokemon": {
        "a": {"objetos": {"sitrusberry": 70, "lifeorb": 20}},
        "b": {"objetos": {"sitrusberry": 60, "lifeorb": 30, "leftovers": 10}},
        "c": {"objetos": {"lifeorb": 80}},
    }}
    resultado = sets_equipo(["b", "a", "c"], uso, {})
    assert {s["nombre"]: s["objeto"] for s in resultado} == {
        "a": "sitrusberry", "b": "leftovers", "c": "lifeorb"}
    assert uso["pokemon"]["b"]["objetos"]["sitrusberry"] == 60


def test_exportacion_exacta(datos, uso, nombres):
    entrada = set_probable("incineroar", uso, datos)
    datos = {"incineroar": {"nombre_showdown": "Incineroar"}}
    esperado = """Incineroar @ Sitrus Berry
Ability: Intimidate
Level: 50
EVs: 32 HP / 4 Def / 30 SpD
Sassy Nature
- Fake Out
- Parting Shot
- Flare Blitz
- Throat Chop"""
    assert a_showdown([entrada], datos, nombres) == esperado
    assert a_showdown([entrada, entrada], datos, nombres) == esperado + "\n\n" + esperado


@pytest.mark.parametrize("regulacion,version,media", [
    (regulacion, version, media)
    for regulacion, versiones in json.loads((FIXTURES / "evaluacion_referencia.json").read_text()).items()
    for version, media in versiones.items()
])
def test_evaluacion_sin_cambios(evaluacion_actual, regulacion, version, media):
    assert resumir(evaluacion_actual[regulacion], version)["puesto_medio"] == pytest.approx(media, abs=0.01)


@pytest.fixture(scope="module")
def evaluacion_actual():
    referencias = json.loads(ruta_equipos_referencia().read_text())
    datos = json.loads(ruta_pokemon_datos().read_text())
    uso = json.loads(ruta_uso_smogon().read_text())
    por_regulacion, _ = evaluar_referencias(referencias, datos, uso)
    return por_regulacion
