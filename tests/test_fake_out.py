import copy
import json

import pytest

from config import ruta_uso_smogon
from puntuacion import PESOS, puntuar
from recomendador import obtener_recomendaciones
from sets import set_probable, sets_equipo


def pokemon():
    return {"tipos": ["normal"], "habilidades": [], "movimientos": ["fakeout"],
            "stats": {"attack": 80, "special-attack": 80, "speed": 80}}


@pytest.mark.parametrize("usuarios,factor", [(0, 1), (1, .5), (2, 0), (3, 0)])
def test_saturacion_fake_out_sin_penalizacion_negativa(usuarios, factor):
    datos = {n: pokemon() for n in ["uno", "dos", "tres", "candidato"]}
    equipo = ["uno", "dos", "tres"][:usuarios]
    assert puntuar(equipo, "candidato", datos, aplicar_antisinergias=False)["fake"] == PESOS["fake"] * factor


def datos_sets(porcentaje=40, choice=False):
    datos = {n: pokemon() for n in ["uno", "dos", "tres"]}
    movimientos = {
        n: {"categoria": categoria} for n, categoria in [
            ("fakeout", "Physical"), ("especial", "Special"), ("ataque1", "Physical"),
            ("ataque2", "Physical"), ("ataque3", "Physical"), ("protect", "Status"),
            ("reemplazo", "Physical"),
        ]
    }
    uso = {n: {"uso": 1, "variantes": {n: {
        "uso": 1, "movimientos": {"fakeout": porcentaje if n == "tres" else 90,
            "ataque1": 39, "ataque2": 38, "ataque3": 37, "especial": 36, "protect": 35, "reemplazo": 34},
        "spreads": {"Adamant:2/32/0/0/0/32": 100},
        "objetos": {"choicescarf": 100} if choice and n == "tres" else {},
    }}} for n in datos}
    return datos, uso, movimientos


@pytest.mark.parametrize("porcentaje,conserva", [(49.99, False), (50, True), (90, True)])
def test_tercer_fake_out_segun_uso_de_variante(porcentaje, conserva):
    datos, uso, movimientos = datos_sets(porcentaje)
    copia = copy.deepcopy(uso)
    equipo = list(datos)
    assert "fakeout" in set_probable("tres", uso, datos, movimientos)["movimientos"]
    resultado = sets_equipo(equipo, uso, datos, movimientos)
    assert ("fakeout" in resultado[2]["movimientos"]) is conserva
    assert all("fakeout" in s["movimientos"] for s in resultado[:2])
    assert len(resultado[2]["movimientos"]) == 4
    assert "especial" not in resultado[2]["movimientos"]
    if not conserva:
        assert "protect" in resultado[2]["movimientos"]
    assert uso == copia


def test_reemplazo_respeta_choice_y_orientacion():
    datos, uso, movimientos = datos_sets(choice=True)
    resultado = sets_equipo(list(datos), uso, datos, movimientos)[2]
    assert resultado["objeto"] == "choicescarf"
    assert "reemplazo" in resultado["movimientos"]
    assert {"fakeout", "protect", "especial"}.isdisjoint(resultado["movimientos"])


def test_dos_usuarios_no_pierden_fake_out_minoritario():
    datos, uso, movimientos = datos_sets()
    resultado = sets_equipo(["uno", "tres"], uso, datos, movimientos)
    assert all("fakeout" in s["movimientos"] for s in resultado)


def test_saturacion_usa_variante_elegida_y_no_agregado():
    datos, uso, movimientos = datos_sets()
    uso["tres"]["movimientos"] = {"fakeout": 99}
    uso["tres"]["variantes"]["otra"] = {**uso["tres"]["variantes"]["tres"], "movimientos": {"fakeout": 80}}
    resultado = sets_equipo(list(datos), uso, datos, movimientos, variantes={"tres": "tres"})
    assert "fakeout" not in resultado[2]["movimientos"]
    resultado = sets_equipo(list(datos), uso, datos, movimientos, variantes={"tres": "otra"})
    assert "fakeout" in resultado[2]["movimientos"]


@pytest.mark.skipif(not ruta_uso_smogon().exists(), reason="No hay uso de Smogon disponible")
def test_frankfurt_conserva_tres_fake_out(datos):
    uso = json.loads(ruta_uso_smogon().read_text(encoding="utf-8"))
    equipo = ["incineroar", "rillaboom", "raichu"]
    resultado = sets_equipo(equipo, uso, datos)
    assert len(resultado) == 3
    assert all("fakeout" in s["movimientos"] for s in resultado)


@pytest.mark.parametrize("porcentaje,avisa", [(19.99, False), (20, True), (49.99, True), (50, False), (90, False)])
def test_aviso_fake_out_solo_para_candidato_minoritario(porcentaje, avisa):
    datos = {n: pokemon() for n in ["uno", "dos", "candidato"]}
    uso = {n: {"movimientos": {"fakeout": porcentaje if n == "candidato" else 90}} for n in datos}
    resultado = obtener_recomendaciones(["uno", "dos"], datos, uso, aplicar_antisinergias=False)
    assert ("⚠️ ya hay 2 Fake Out: su set no debería llevarlo" in resultado[0]["aporta"]) is avisa


def test_explicaciones_solo_para_top_cli(monkeypatch, capsys):
    import recomendador
    datos = {n: pokemon() for n in ["uno", "dos", "tres", "candidato"]}
    monkeypatch.setattr(recomendador, "cargar_uso_smogon", lambda: {})
    monkeypatch.setattr(recomendador.json, "loads", lambda *args: datos)
    llamadas = []
    monkeypatch.setattr(recomendador, "explicar", lambda equipo, candidato, *args: llamadas.append(candidato) or [{"id": "prueba", "texto": "Motivo visible"}])
    assert len(obtener_recomendaciones(["uno"], datos)) == 3
    assert llamadas == []
    resultado = recomendador.recomendar(["uno"], top_n=2)
    assert llamadas == [r["nombre"] for r in resultado]
    salida = capsys.readouterr().out
    assert "Debilidades de tu equipo" in salida
    assert salida.count("Por qué: Motivo visible") == 2


def test_aviso_respeta_variante_elegida_aunque_agregado_diga_otro_uso():
    datos, uso, movimientos = datos_sets()
    uso["tres"]["movimientos"] = {"fakeout": 99}
    uso["tres"]["variantes"]["otra"] = {
        **uso["tres"]["variantes"]["tres"], "movimientos": {"fakeout": 80},
    }
    for variante, avisa in [("tres", True), ("otra", False)]:
        resultado = obtener_recomendaciones(["uno", "dos"], datos, uso,
                                           variantes={"tres": variante})
        assert ("ya hay 2 Fake Out" in resultado[0]["aporta"]) is avisa
