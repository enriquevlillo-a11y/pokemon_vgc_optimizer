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


def _habilidad_base(nombre, estadisticas, datos):
    """Descarta habilidades de Mega y prioriza el uso entre las de la base."""
    habilidades = [normalizar_id(habilidad["nombre"] if isinstance(habilidad, dict) else habilidad)
                   for habilidad in datos.get(nombre, {}).get("habilidades", [])]
    if not habilidades:
        return None
    uso = {normalizar_id(habilidad): porcentaje
           for habilidad, porcentaje in estadisticas.get("habilidades", {}).items()}
    # max conserva la primera habilidad de la base cuando ninguna tiene uso.
    return max(habilidades, key=lambda habilidad: uso.get(habilidad, 0))


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


def _movimientos_probables(estadisticas, orientacion, movimientos, objeto):
    categoria_descartada = {"fisica": "special", "especial": "physical"}.get(orientacion)
    choice = normalizar_id(objeto or "") in {"choicescarf", "choiceband", "choicespecs"}
    ataques = []
    for movimiento in _ordenados(estadisticas.get("movimientos", {})):
        identificador = normalizar_id(movimiento)
        categoria = movimientos.get(identificador, {}).get("categoria", "").lower()
        if categoria == categoria_descartada:
            continue
        if choice and (identificador == "protect" or categoria == "status"):
            continue
        ataques.append(movimiento)
        if len(ataques) == 4:
            break
    return ataques


def set_probable(nombre, uso_smogon, datos, movimientos=None):
    """Elige spread y movimientos compatibles con la orientación dominante.

    Smogon publica distribuciones separadas; esta aproximación evita combinar
    ataques físicos y especiales de orientaciones distintas. Si falta el
    catálogo de movimientos, no se filtra por categoría. Protect se omite
    siempre con objetos Choice. La habilidad debe pertenecer a la especie base.
    """
    estadisticas = entrada_uso(nombre, uso_smogon)
    if not estadisticas:
        return None
    if movimientos is None:
        movimientos = _cargar_movimientos()
    objetos = _objetos(estadisticas, datos)
    orientacion, naturaleza, puntos = _spread(estadisticas)
    objeto = objetos[0] if objetos else None
    ataques = _movimientos_probables(estadisticas, orientacion, movimientos, objeto)
    return {"nombre": nombre, "habilidad": _habilidad_base(nombre, estadisticas, datos),
            "objeto": objeto,
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
        entrada["movimientos"] = _movimientos_probables(
            uso[entrada["nombre"]], entrada["orientacion"], movimientos, entrada["objeto"]
        )
    return sets
