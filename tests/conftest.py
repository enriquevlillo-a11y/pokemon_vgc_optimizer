import json
from pathlib import Path

import pytest

from config import ruta_pokemon_datos, ruta_uso_smogon


@pytest.fixture(scope="session")
def datos():
    return json.loads(ruta_pokemon_datos().read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def uso_smogon():
    return json.loads(ruta_uso_smogon().read_text(encoding="utf-8"))


@pytest.fixture
def fixture_sets():
    return json.loads((Path(__file__).parent / "fixtures" / "sets_exportacion.json").read_text(encoding="utf-8"))
