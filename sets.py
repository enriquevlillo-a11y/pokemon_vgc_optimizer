"""Sets probables a partir de las estadísticas de Smogon."""

import json

from config import ruta_movimientos
from importar_showdown import normalizar_id
from datos_uso import entrada_uso

ESTADISTICAS = ("hp", "attack", "defense", "special-attack", "special-defense", "speed")


def _ordenados(valores):
    return sorted(valores, key=lambda clave: (-valores[clave], clave))


def _objetos(estadisticas, datos):
    objetos = _ordenados(estadisticas.get("objetos", {}))
    megas = estadisticas.get("megas", {})
    if sum(megas.values()) > 50:
        for mega in _ordenados(megas):
            piedra = datos.get(mega, {}).get("objeto_mega")
            if piedra:
                piedra = normalizar_id(piedra)
                return [piedra] + [objeto for objeto in objetos if objeto != piedra]
    return objetos


def _spread(estadisticas):
    """Suma usos por orientación y escoge el spread más usado en la ganadora."""
    spreads = []
    porcentajes = {"fisica": 0, "especial": 0}
    for spread in _ordenados(estadisticas.get("spreads", {})):
        try:
            naturaleza, reparto = spread.split(":")
            puntos = [int(punto) for punto in reparto.split("/")]
        except (ValueError, AttributeError):
            continue
        if len(puntos) != 6 or any(not 0 <= punto <= 32 for punto in puntos):
            continue
        orientacion = "fisica" if puntos[1] > puntos[3] else "especial" if puntos[3] > puntos[1] else "apoyo"
        spreads.append((orientacion, naturaleza, dict(zip(ESTADISTICAS, puntos))))
        if orientacion in porcentajes:
            porcentajes[orientacion] += estadisticas["spreads"][spread]
    orientacion = max(porcentajes, key=porcentajes.get) if any(porcentajes.values()) else "apoyo"
    elegido = next((spread for spread in spreads if spread[0] == orientacion), None)
    return elegido or ("apoyo", None, dict.fromkeys(ESTADISTICAS, 0))


def _cargar_movimientos():
    ruta = ruta_movimientos()
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}


def set_probable(nombre, uso_smogon, datos, movimientos=None):
    """Elige spread y movimientos compatibles con la orientación dominante.

    Smogon publica distribuciones separadas; esta aproximación evita combinar
    ataques físicos y especiales de orientaciones distintas. Si falta el
    catálogo de movimientos, se conserva el orden de uso sin filtrar.
    """
    estadisticas = entrada_uso(nombre, uso_smogon)
    if not estadisticas:
        return None
    if movimientos is None:
        movimientos = _cargar_movimientos()
    habilidades = _ordenados(estadisticas.get("habilidades", {}))
    objetos = _objetos(estadisticas, datos)
    orientacion, naturaleza, puntos = _spread(estadisticas)
    categoria_descartada = {"fisica": "special", "especial": "physical"}.get(orientacion)
    ataques = [movimiento for movimiento in _ordenados(estadisticas.get("movimientos", {}))
               if movimientos.get(normalizar_id(movimiento), {}).get("categoria", "").lower()
               != categoria_descartada][:4]
    return {"nombre": nombre, "habilidad": habilidades[0] if habilidades else None,
            "objeto": objetos[0] if objetos else None,
            "movimientos": ataques, "orientacion": orientacion,
            "naturaleza": naturaleza, "puntos": puntos}


def sets_equipo(equipo, uso_smogon, datos, movimientos=None):
    """Resuelve Item Clause conservando cada objeto en quien más lo usa."""
    if movimientos is None:
        movimientos = _cargar_movimientos()
    sets = [set_probable(nombre, uso_smogon, datos, movimientos) for nombre in equipo]
    sets = [entrada for entrada in sets if entrada is not None]
    uso = (uso_smogon or {}).get("pokemon", uso_smogon or {})
    # Los objetos inicialmente elegidos quedan reservados para sus ganadores.
    ganadores = {}
    for entrada in sets:
        objeto = entrada["objeto"]
        if not objeto:
            continue
        porcentaje = uso[entrada["nombre"]].get("objetos", {}).get(objeto, 0)
        if objeto not in ganadores or porcentaje > ganadores[objeto][0]:
            ganadores[objeto] = (porcentaje, entrada)
    ocupados = set(ganadores)
    for entrada in sets:
        objeto = entrada["objeto"]
        if not objeto or ganadores[objeto][1] is entrada:
            continue
        alternativas = _ordenados(uso[entrada["nombre"]].get("objetos", {}))
        entrada["objeto"] = next((objeto for objeto in alternativas if objeto not in ocupados), None)
        if entrada["objeto"]:
            ocupados.add(entrada["objeto"])
    return sets
