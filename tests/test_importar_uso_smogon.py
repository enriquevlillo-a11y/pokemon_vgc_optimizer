import json
from pathlib import Path

import pytest

from importar_uso_smogon import nombres_desconocidos, transformar_estadisticas


FIXTURE = Path(__file__).parent / "fixtures" / "uso_smogon.json"


@pytest.fixture
def estadisticas():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_normaliza_porcentajes_y_nombres(estadisticas):
    resultado = transformar_estadisticas(estadisticas, "2026-09", 1760)
    mr_mime = resultado["pokemon"]["mr-mime"]

    assert mr_mime["uso"] == 12.5
    assert mr_mime["habilidades"] == {
        "screen-cleaner": 75.0,
        "soundproof": 25.0,
    }
    assert mr_mime["objetos"]["safety-goggles"] == 75.0
    assert mr_mime["companeros"]["flabebe"] == 75.0
    assert sum(mr_mime["movimientos"].values()) < 400
    assert mr_mime["movimientos"]["move-01"] == pytest.approx(61.5384615)
    assert resultado["info"] == {
        "mes": "2026-09",
        "rating": 1760,
        "combates": 1234,
    }


def test_filtra_uso_bajo_y_limita_los_top(estadisticas):
    resultado = transformar_estadisticas(estadisticas, "2026-09", 1760)

    assert "farfetchd" not in resultado["pokemon"]
    assert len(resultado["pokemon"]["mr-mime"]["movimientos"]) == 10
    assert len(resultado["pokemon"]["mr-mime"]["spreads"]) == 5
    assert "move-11" not in resultado["pokemon"]["mr-mime"]["movimientos"]


def test_informa_nombres_originales_que_no_existen(estadisticas):
    conocidos = {"mr-mime": {}}

    assert nombres_desconocidos(estadisticas, conocidos) == ["Farfetch’d"]
