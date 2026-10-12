"""Tests de B1 (preview como juego) que no necesitan Showdown."""

import json
from pathlib import Path

import numpy as np
import pytest

from bots.preview_juego import _repartir, planes, resolver_juego

BASE = Path(__file__).resolve().parents[1]
EQ = BASE / "tests" / "fixtures" / "final_frankfurt"


@pytest.fixture(scope="module")
def datos():
    return json.loads((BASE / "data" / "reg_m_c" / "pokemon_datos.json").read_text(encoding="utf-8"))


def test_noventa_planes_distintos(datos):
    lista = planes((EQ / "eric.txt").read_text(encoding="utf-8"), datos)
    assert len(lista) == 90
    # Mismo par de líderes en distinto orden no se repite; los 4 siempre son distintos.
    claves = {(frozenset(p[:2]), frozenset(p[2:])) for p in lista}
    assert len(claves) == 90
    assert all(len(set(p)) == 4 for p in lista)
    # El plan E2 de Eric (líderes Garchomp + Gholdengo) está, con la reserva en cualquier orden.
    assert (frozenset({"garchomp", "gholdengo"}), frozenset({"volcarona", "incineroar"})) in claves


def test_piedra_papel_tijera_es_uniforme():
    filas, columnas, valor = resolver_juego([[0.5, 0, 1], [1, 0.5, 0], [0, 1, 0.5]])
    assert np.allclose(filas, 1 / 3, atol=0.02)
    assert np.allclose(columnas, 1 / 3, atol=0.02)
    assert valor == pytest.approx(0.5, abs=0.01)


def test_estrategias_puras_con_punto_de_silla():
    # Fila 0 domina; la columna 1 es la mejor respuesta: valor 0,4.
    filas, columnas, valor = resolver_juego([[0.7, 0.4], [0.6, 0.3]])
    assert filas[0] > 0.95 and columnas[1] > 0.95
    assert valor == pytest.approx(0.4, abs=0.01)


def test_mezcla_no_trivial():
    # Pares e impares asimétrico: equilibrio filas (0,4; 0,6), valor 0,6.
    filas, _, valor = resolver_juego([[0.9, 0.4], [0.4, 0.733333]])
    assert filas[0] == pytest.approx(0.4, abs=0.03)
    assert valor == pytest.approx(0.6, abs=0.01)


def test_repartir_respeta_pesos_y_minimo():
    reparto = _repartir([0.75, 0.25, 0.0], ["a", "b", "c"], 8)
    assert [p for p, _, _ in reparto] == ["a", "b"]
    assert [n for _, n, _ in reparto] == [6, 2]
    assert sum(w for _, _, w in reparto) == pytest.approx(1)
