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
    assert mr_mime["objetos"]["safety-goggles"] == 7.5
    assert mr_mime["companeros"]["flabebe"] == 7.5
    assert mr_mime["movimientos"]["move-01"] == 30.0
    assert resultado["info"] == {
        "mes": "2026-09",
        "rating": 1760,
        "formato": None,
        "combates": 1234,
    }


def test_filtra_uso_bajo_y_limita_los_top(estadisticas):
    resultado = transformar_estadisticas(estadisticas, "2026-09", 1760)

    assert "farfetchd" not in resultado["pokemon"]
    assert len(resultado["pokemon"]["mr-mime"]["movimientos"]) == 11
    assert len(resultado["pokemon"]["mr-mime"]["spreads"]) == 5
    assert resultado["pokemon"]["mr-mime"]["movimientos"]["move-11"] == 5
    assert "move-12" not in resultado["pokemon"]["mr-mime"]["movimientos"]


def test_agrega_megas_y_normaliza_companeros(estadisticas):
    resultado = transformar_estadisticas(estadisticas, "2026-09", 1760)

    charizard = resultado["pokemon"]["charizard"]
    assert charizard["uso"] == 3.0
    assert charizard["recuento"] == 100
    assert charizard["megas"] == {"charizard-mega-y": 70.0}
    assert charizard["habilidades"] == {"drought": 70.0, "blaze": 30.0}
    assert charizard["companeros"]["floette-eternal"] == 50.0
    assert "floette" not in resultado["pokemon"]
    assert "floette-eternal" in resultado["pokemon"]


def test_informa_nombres_originales_que_no_existen(estadisticas):
    conocidos = {"mr-mime": {}, "charizard": {}, "floette-eternal": {}}

    assert nombres_desconocidos(estadisticas, conocidos) == ["Farfetch’d"]
