import json
from pathlib import Path

import pytest

import sets
from config import ruta_uso_smogon
from importar_showdown import extraer_movimientos

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def catalogo(monkeypatch, tmp_path):
    movimientos = extraer_movimientos(FIXTURES / "moves.ts", FIXTURES / "champions-moves.ts")
    movimientos.update({
        nombre: {"categoria": categoria}
        for categoria, nombres in {
            "Physical": ["dragonclaw", "stompingtantrum", "earthquake", "scaleshot",
                         "grassyglide", "woodhammer", "highhorsepower", "uturn",
                         "lastrespects", "aquajet", "wavecrash", "flipturn"],
            "Special": ["powergem", "earthpower", "dragonpulse", "dracometeor",
                        "flamethrower", "zapcannon", "focusblast"],
            "Status": ["encore"],
        }.items() for nombre in nombres
    })
    ruta = tmp_path / "movimientos.json"
    ruta.write_text(json.dumps(movimientos))
    monkeypatch.setattr(sets, "ruta_movimientos", lambda: ruta)
    return movimientos


def test_sets_reales_coherentes(datos, uso_smogon, catalogo):
    garchomp = sets.set_probable("garchomp", uso_smogon, datos)
    assert garchomp["orientacion"] == "fisica"
    assert garchomp["naturaleza"] in {"Jolly", "Adamant"}
    assert len(garchomp["movimientos"]) == 4
    assert all(catalogo[m]["categoria"] != "Special" for m in garchomp["movimientos"])
    assert sets.set_probable("rillaboom", uso_smogon, datos)["naturaleza"] == "Adamant"
    raichu = sets.set_probable("raichu", uso_smogon, datos)
    assert {"zapcannon", "focusblast"} <= set(raichu["movimientos"])
    incineroar = sets.set_probable("incineroar", uso_smogon, datos)
    assert {"fakeout", "partingshot"} <= set(incineroar["movimientos"])
    assert incineroar["habilidad"] == "intimidate"


@pytest.mark.parametrize("fisico,especial,orientacion,naturaleza,ataques", [
    (40, 30, "fisica", "Adamant", ["protect", "fakeout", "rockslide", "partingshot"]),
    (30, 40, "especial", "Modest", ["protect", "zapcannon", "focusblast", "partingshot"]),
    (0, 0, "apoyo", "Sassy", ["protect", "zapcannon", "fakeout", "focusblast"]),
])
def test_filtra_ataques_y_conserva_status(catalogo, fisico, especial, orientacion, naturaleza, ataques):
    uso = {"pokemon": {"prueba": {
        "spreads": {"Adamant:0/32/0/0/0/32": fisico, "Modest:0/0/0/32/0/32": especial,
                    "Sassy:32/0/4/0/30/0": 100},
        "movimientos": {"protect": 100, "zapcannon": 95, "fakeout": 90, "focusblast": 85,
                        "rockslide": 80, "partingshot": 75},
    }}}
    entrada = sets.set_probable("prueba", uso, {})
    assert entrada["orientacion"] == orientacion
    assert entrada["naturaleza"] == naturaleza
    assert entrada["movimientos"] == ataques


def test_suma_spreads_y_no_solo_el_mas_usado(catalogo):
    uso = {"pokemon": {"prueba": {"spreads": {
        "Modest:0/0/0/32/0/32": 45,
        "Jolly:0/32/0/0/0/32": 30,
        "Adamant:0/32/0/0/0/32": 25,
    }}}}
    entrada = sets.set_probable("prueba", uso, {})
    assert entrada["orientacion"] == "fisica"
    assert entrada["naturaleza"] == "Jolly"


def test_catalogo_ausente_no_filtra(monkeypatch, tmp_path):
    monkeypatch.setattr(sets, "ruta_movimientos", lambda: tmp_path / "no-existe.json")
    uso = json.loads(ruta_uso_smogon().read_text())
    raichu = sets.set_probable("raichu", uso, {})
    assert raichu["orientacion"] == "apoyo"
    assert raichu["movimientos"] == ["protect", "zapcannon", "focusblast", "fakeout"]


def test_sets_equipo_aplica_filtro(catalogo):
    uso = {"pokemon": {"prueba": {
        "spreads": {"Modest:0/0/0/32/0/32": 100},
        "movimientos": {"fakeout": 100, "protect": 95, "focusblast": 90},
    }}}
    assert sets.sets_equipo(["prueba"], uso, {})[0]["movimientos"] == ["protect", "focusblast"]


def test_desempate_redondea_a_seis_decimales(monkeypatch):
    import recomendador

    monkeypatch.setattr(recomendador, "puntuar", lambda equipo, nombre, *args: {
        "total": {"salazzle": 3.3833333333333333, "gardevoir": 3.383333333333333}[nombre]
    })
    monkeypatch.setattr(recomendador, "roles_de", lambda *args: {})
    monkeypatch.setattr(recomendador, "_aportes", lambda *args: "")
    datos = {nombre: {"tipos": []} for nombre in ["salazzle", "gardevoir"]}
    recomendaciones = recomendador.obtener_recomendaciones([], datos, aplicar_antisinergias=False)
    assert [r["nombre"] for r in recomendaciones] == ["gardevoir", "salazzle"]


@pytest.mark.parametrize("nombre,habilidad,nombre_showdown", [
    ("charizard", "blaze", "Charizard"),
    ("gardevoir", "trace", "Gardevoir"),
    ("floette-eternal", "flowerveil", "Floette-Eternal"),
    ("raichu", "lightningrod", "Raichu"),
    ("incineroar", "intimidate", "Incineroar"),
])
def test_exporta_habilidad_base_real(datos, uso_smogon, catalogo, nombre, habilidad, nombre_showdown):
    from exportar import a_showdown
    from importar_showdown import extraer_nombres, normalizar_id

    entrada = sets.set_probable(nombre, uso_smogon, datos)
    base = {normalizar_id(h["nombre"]) for h in datos[nombre]["habilidades"]}
    assert entrada["habilidad"] == habilidad
    assert entrada["habilidad"] in base
    nombres = {"habilidades": extraer_nombres(FIXTURES / "abilities.ts")}
    datos_exportacion = {nombre: {**datos[nombre], "nombre_showdown": nombre_showdown}}
    texto = a_showdown([entrada], datos_exportacion, nombres)
    assert "Ability: " + nombres["habilidades"][habilidad] in texto.splitlines()


@pytest.mark.parametrize("habilidades_uso,esperada", [
    ({"drought": 99, "solar-power": 0.8, "blaze": 0.2}, "solarpower"),
    ({"drought": 100}, "blaze"),
    ({"drought": 100, "solarpower": 0, "blaze": 0}, "blaze"),
])
def test_habilidad_base_mayor_uso_o_primera(habilidades_uso, esperada):
    datos = {"charizard": {"habilidades": [{"nombre": "blaze"}, {"nombre": "solar-power"}]}}
    uso = {"charizard": {"habilidades": habilidades_uso}}
    assert sets.set_probable("charizard", uso, datos, movimientos={})["habilidad"] == esperada


def test_basculegion_choice_scarf_sin_protect(datos, uso_smogon, catalogo):
    entrada = sets.set_probable("basculegion", uso_smogon, datos)
    assert entrada["objeto"] == "choicescarf"
    assert entrada["movimientos"] == ["lastrespects", "aquajet", "wavecrash", "flipturn"]


@pytest.mark.parametrize("objeto", ["choicescarf", "choiceband", "choicespecs"])
def test_choice_excluye_status(objeto, catalogo):
    uso = {"prueba": {
        "objetos": {objeto: 100},
        "movimientos": {"protect": 100, "encore": 95, "partingshot": 90,
                        "fakeout": 85, "rockslide": 80, "flareblitz": 75, "throatchop": 70},
    }}
    entrada = sets.set_probable("prueba", uso, {})
    assert entrada["movimientos"] == ["fakeout", "rockslide", "flareblitz", "throatchop"]


def test_choice_sin_catalogo_omite_protect():
    uso = {"prueba": {"objetos": {"choicescarf": 100}, "movimientos": {"protect": 100, "fakeout": 90}}}
    assert sets.set_probable("prueba", uso, {}, movimientos={})["movimientos"] == ["fakeout"]


def test_item_clause_recalcula_movimientos_al_pasar_a_choice(catalogo):
    uso = {"pokemon": {
        "a": {"objetos": {"lifeorb": 80}},
        "b": {"objetos": {"lifeorb": 70, "choicescarf": 30},
              "movimientos": {"protect": 100, "encore": 95, "fakeout": 90, "rockslide": 85}},
    }}
    resultado = sets.sets_equipo(["a", "b"], uso, {})
    assert resultado[1]["objeto"] == "choicescarf"
    assert resultado[1]["movimientos"] == ["fakeout", "rockslide"]
