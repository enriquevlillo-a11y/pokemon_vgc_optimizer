"""Revisa respuestas ofensivas y defensivas frente al metajuego."""

import json

from config import ruta_movimientos
from importar_showdown import normalizar_id
from motor_tipos import calcular_defensas


def revisar_equipo(equipo, datos, uso_smogon=None, movimientos=None):
    """Devuelve amenazas por uso y los miembros que les pegan o las resisten.

    Con Smogon solo se consideran ataques frecuentes y con potencia positiva.
    Sin Smogon se conserva la aproximación ofensiva por tipos propios.
    """
    uso = (uso_smogon or {}).get("pokemon", {})
    if movimientos is None:
        ruta = ruta_movimientos()
        movimientos = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
    ataques = {}
    for miembro in equipo:
        estadisticas = uso.get(miembro)
        if estadisticas:
            ataques[miembro] = [
                (movimiento.get("tipo", "").lower(), movimiento.get("nombre", nombre))
                for nombre, porcentaje in estadisticas.get("movimientos", {}).items()
                if porcentaje >= 20
                for movimiento in [movimientos.get(normalizar_id(nombre), {})]
                if movimiento.get("categoria", "").lower() not in ("", "status")
                and movimiento.get("potencia", 0) > 0
            ]
        else:
            ataques[miembro] = [(tipo, None) for tipo in datos[miembro]["tipos"]]
    resultado = []
    for nombre, estadisticas in sorted(uso.items(), key=lambda par: (-par[1].get("uso", 0), par[0])):
        if nombre not in datos:
            continue
        defensas = calcular_defensas(datos[nombre]["tipos"])
        le_pegan, con, resisten = [], {}, []
        for miembro in equipo:
            efectivos = [movimiento for tipo, movimiento in ataques[miembro]
                         if defensas.get(tipo, 1) > 1]
            if efectivos:
                le_pegan.append(miembro)
                con[miembro] = [movimiento for movimiento in efectivos if movimiento]
            defensas_miembro = calcular_defensas(datos[miembro]["tipos"])
            if all(defensas_miembro[tipo] < 1 for tipo in datos[nombre]["tipos"]):
                resisten.append(miembro)
        resultado.append({"nombre": nombre, "uso": estadisticas.get("uso", 0),
                          "le_pegan": le_pegan, "con": con, "resisten": resisten,
                          "sin_respuesta": not le_pegan})
    return resultado
