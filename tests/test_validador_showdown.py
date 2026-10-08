"""Integración opcional con una instalación local del validador oficial."""

import json
import os
from pathlib import Path
import subprocess

import pytest

from config import ruta_equipos_referencia, ruta_movimientos, ruta_nombres
from exportar import a_showdown
from sets import sets_equipo


@pytest.mark.skipif(not os.environ.get("SHOWDOWN_DIR"), reason="SHOWDOWN_DIR no está definido")
def test_equipos_referencia_validos_en_showdown(datos, uso_smogon):
    referencias = json.loads(ruta_equipos_referencia().read_text(encoding="utf-8"))
    movimientos = json.loads(ruta_movimientos().read_text(encoding="utf-8"))
    nombres = json.loads(ruta_nombres().read_text(encoding="utf-8"))
    directorio = Path(os.environ["SHOWDOWN_DIR"]).resolve()
    for referencia in referencias:
        equipo = sets_equipo(referencia["equipo"], uso_smogon, datos, movimientos)
        texto = a_showdown(equipo, datos, nombres)
        resultado = subprocess.run(
            [str(directorio / "pokemon-showdown"), "validate-team", "gen9championsvgc2026regmc"],
            input=texto, text=True, capture_output=True, cwd=directorio, timeout=60,
        )
        assert resultado.returncode == 0, (
            f"{referencia['nombre']}:\n{resultado.stdout}\n{resultado.stderr}\n{texto}"
        )
