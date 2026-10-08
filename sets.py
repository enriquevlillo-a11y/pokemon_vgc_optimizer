"""Sets probables a partir de las estadísticas de Smogon."""

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


def set_probable(nombre, uso_smogon, datos):
    """Selecciona habilidad, objeto, ataques y spread más usados."""
    estadisticas = entrada_uso(nombre, uso_smogon)
    if not estadisticas:
        return None
    habilidades = _ordenados(estadisticas.get("habilidades", {}))
    objetos = _objetos(estadisticas, datos)
    spreads = _ordenados(estadisticas.get("spreads", {}))
    naturaleza, puntos = spreads[0].split(":") if spreads else (None, "0/0/0/0/0/0")
    return {"nombre": nombre, "habilidad": habilidades[0] if habilidades else None,
            "objeto": objetos[0] if objetos else None,
            "movimientos": _ordenados(estadisticas.get("movimientos", {}))[:4],
            "naturaleza": naturaleza,
            "puntos": dict(zip(ESTADISTICAS, map(int, puntos.split("/"))))}


def sets_equipo(equipo, uso_smogon, datos):
    """Resuelve Item Clause conservando cada objeto en quien más lo usa."""
    sets = [set_probable(nombre, uso_smogon, datos) for nombre in equipo]
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
