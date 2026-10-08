import copy
import json
from pathlib import Path

import pytest

from diagnostico import debilidades_equipo, explicar


def pokemon(tipos=("normal",), movimientos=(), ataque=80):
    return {"tipos": list(tipos), "movimientos": list(movimientos), "habilidades": [],
            "stats": {"attack": ataque, "special-attack": 80, "speed": 80}}


def por_id(resultado):
    return {d["id"]: d for d in resultado}


def test_fake_out_faltante_y_candidato_que_lo_aporta():
    datos = {"aliado": pokemon(), "candidato": pokemon(movimientos=["fakeout"])}
    diagnostico = por_id(debilidades_equipo(["aliado"], datos, {}, movimientos={}))
    assert diagnostico["sin_fake_out"]["gravedad"] == "alta"
    motivos = por_id(explicar(["aliado"], "candidato", datos, {}, movimientos={}))
    assert "Fake Out" in motivos["sin_fake_out"]["texto"]
    assert "sin_fake_out" not in por_id(debilidades_equipo(["aliado", "candidato"], datos, {}, movimientos={}))
    assert "sin_win_condition" not in motivos


@pytest.mark.parametrize("control,gravedad", [(None, "alta"), ("icywind", "media"), ("electroweb", "media"), ("tailwind", None), ("trickroom", None)])
def test_control_fuerte_debil_y_ausente(control, gravedad):
    datos = {"aliado": pokemon(movimientos=[control] if control else [])}
    diagnostico = por_id(debilidades_equipo(["aliado"], datos, {}, movimientos={}))
    if gravedad is None:
        assert "sin_control_velocidad" not in diagnostico
    else:
        assert diagnostico["sin_control_velocidad"]["gravedad"] == gravedad
        if gravedad == "media":
            assert "débil" in diagnostico["sin_control_velocidad"]["texto"]


def test_control_debil_solo_explica_una_mejora_parcial():
    datos = {"aliado": pokemon(), "debil": pokemon(movimientos=["icywind"]),
             "fuerte": pokemon(movimientos=["tailwind"])}
    assert "débil" in por_id(explicar(["aliado"], "debil", datos, {}, movimientos={}))["sin_control_velocidad"]["texto"]
    assert "sin_control_velocidad" not in por_id(explicar(["debil"], "aliado", datos, {}, movimientos={}))
    assert "Tailwind" in por_id(explicar(["debil"], "fuerte", datos, {}, movimientos={}))["sin_control_velocidad"]["texto"]


def test_tres_debiles_a_fuego_y_resistencia_agua():
    datos = {n: pokemon([tipo]) for n, tipo in [("uno", "grass"), ("dos", "steel"), ("tres", "ice"), ("agua", "water")]}
    equipo = ["uno", "dos", "tres"]
    assert por_id(debilidades_equipo(equipo, datos, {}, movimientos={}))["tipo_fire"]["gravedad"] == "alta"
    motivo = por_id(explicar(equipo, "agua", datos, {}, movimientos={}))["tipo_fire"]["texto"]
    assert "Resiste" in motivo and "agua" in motivo
    assert "tipo_fire" not in por_id(debilidades_equipo(equipo + ["agua"], datos, {}, movimientos={}))
    assert "tipo_fire" not in por_id(debilidades_equipo(equipo[:2], datos, {}, movimientos={}))


def test_inmunidad_por_habilidad_de_variante_cubre_tipo():
    datos = {n: pokemon(["grass"]) for n in ["uno", "dos", "tres", "inmune"]}
    uso = {"inmune": {"uso": 1, "variantes": {
        "inmune": {"uso": 1, "habilidades": {"flashfire": 100}},
    }}}
    equipo = ["uno", "dos", "tres"]
    motivo = por_id(explicar(equipo, "inmune", datos, uso, movimientos={}))["tipo_fire"]["texto"]
    assert "inmune" in motivo and "flashfire" in motivo
    assert "tipo_fire" not in por_id(debilidades_equipo(equipo + ["inmune"], datos, uso, movimientos={}))


def test_amenaza_mejora_y_explicacion_menciona_movimiento_y_mega():
    datos = {"aliado": pokemon(), "roca": pokemon(["rock"]), "charizard": pokemon(["fire", "flying"]),
             "charizard-mega-y": {**pokemon(["fire", "flying"]), "nombre_showdown": "Charizard-Mega-Y"}}
    uso = {"charizard": {"uso": 20, "megas": {"charizard-mega-y": 90}},
           "roca": {"uso": 1, "movimientos": {"rockslide": 100}}}
    movimientos = {"rockslide": {"tipo": "rock", "categoria": "Physical", "potencia": 75, "nombre": "Rock Slide"}}
    diagnostico = por_id(debilidades_equipo(["aliado"], datos, uso, movimientos))
    assert "nadie le pega superefectivo" in diagnostico["amenaza_charizard"]["texto"]
    motivos = por_id(explicar(["aliado"], "roca", datos, uso, movimientos))
    texto = motivos["amenaza_charizard"]["texto"]
    assert all(p in texto for p in ["Charizard-Mega-Y", "Rock Slide", "'sin respuesta'", "'cubierta'"])
    assert "amenaza_charizard" not in por_id(explicar(["roca"], "aliado", datos, uso, movimientos))


def test_amenaza_en_riesgo_y_mejora_sin_respuesta_a_riesgo():
    datos = {n: pokemon(["fire"]) for n in ["uno", "dos", "tres"]}
    datos.update({"agua": pokemon(["water"]), "planta": pokemon(["grass"])})
    uso = {"agua": {"uso": 20}}
    equipo = ["uno", "dos", "tres"]
    texto = por_id(explicar(equipo, "planta", datos, uso, movimientos={}))["amenaza_agua"]["texto"]
    assert "'sin respuesta'" in texto and "'en riesgo'" in texto
    diagnostico = por_id(debilidades_equipo(equipo + ["planta"], datos, uso, movimientos={}))
    riesgo = diagnostico["amenaza_agua"]
    assert riesgo["gravedad"] == "media"
    assert all(n in riesgo["texto"] for n in ["débiles", "Uno", "Dos", "Tres"])


def test_roles_y_explicaciones_respetan_seleccion_de_variante():
    fixture = json.loads((Path(__file__).parent / "fixtures" / "variantes_smogon.json").read_text())
    datos, uso, movimientos = (fixture[k] for k in ("datos", "uso", "movimientos"))
    equipo = ["garchomp"]
    assert "sin_control_velocidad" in por_id(debilidades_equipo(equipo + ["dragonite"], datos, uso, movimientos))
    seleccion = {"dragonite": "dragonite-mega"}
    assert "sin_control_velocidad" not in por_id(debilidades_equipo(equipo + ["dragonite"], datos, uso, movimientos, seleccion))
    assert "Tailwind" in por_id(explicar(equipo, "dragonite", datos, uso, movimientos, seleccion))["sin_control_velocidad"]["texto"]
    assert "sin_control_velocidad" not in por_id(explicar(equipo, "dragonite", datos, uso, movimientos))


def test_roles_intimidate_ofensivo_orden_estable_y_sin_mutaciones():
    datos = {"aliado": pokemon(), "candidato": pokemon(ataque=120)}
    datos["candidato"]["habilidades"] = ["intimidate"]
    original = copy.deepcopy(datos)
    diagnostico = debilidades_equipo(["aliado"], datos, {}, movimientos={})
    assert por_id(diagnostico)["sin_intimidate"]["gravedad"] == "media"
    assert por_id(diagnostico)["sin_win_condition"]["gravedad"] == "alta"
    assert diagnostico == sorted(diagnostico, key=lambda d: (d["gravedad"] != "alta", d["id"]))
    motivos = por_id(explicar(["aliado"], "candidato", datos, {}, movimientos={}))
    assert {"sin_intimidate", "sin_win_condition"} <= motivos.keys()
    assert datos == original
