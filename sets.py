"""Sets probables de Smogon y sets genéricos para especies sin datos de uso."""

import json

from config import ruta_movimientos
from importar_showdown import normalizar_id
from importar_uso_smogon import nombre_base, SUFIJO_MEGA
from datos_uso import entrada_uso, entrada_variante, seleccionar_variante

ESTADISTICAS = ("hp", "attack", "defense", "special-attack", "special-defense", "speed")


def _ordenados(valores):
    return sorted(valores, key=lambda clave: (-valores[clave], clave))


def _objetos(estadisticas, datos, variante=None):
    if variante is not None:
        forma = datos.get(variante, {})
        if forma.get("es_mega") or SUFIJO_MEGA.search(variante):
            piedra = forma.get("objeto_mega")
            if not piedra:
                raise ValueError(f"Falta objeto_mega para {variante}")
            return [normalizar_id(piedra)]
        return _ordenados(estadisticas.get("objetos", {}))
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


def _habilidad_variante(nombre, variante, estadisticas, uso_smogon, datos):
    """Exporta una habilidad legal de la base, priorizando la de la Mega."""
    if variante is None or not (datos.get(variante, {}).get("es_mega") or SUFIJO_MEGA.search(variante)):
        return _habilidad_base(nombre, estadisticas, datos)
    def habilidades(forma):
        return [normalizar_id(h["nombre"] if isinstance(h, dict) else h)
                for h in datos.get(forma, {}).get("habilidades", [])]
    comunes = set(habilidades(nombre)) & set(habilidades(variante))
    if not comunes:
        comunes = set(habilidades(nombre)) & {
            normalizar_id(h) for h in estadisticas.get("habilidades", {})
        }
    if comunes:
        uso = {normalizar_id(h): p for h, p in estadisticas.get("habilidades", {}).items()}
        return min(comunes, key=lambda h: (-uso.get(h, 0), h))
    variantes = (entrada_uso(nombre, uso_smogon) or {}).get("variantes", {})
    base = next((v for forma, v in variantes.items()
                 if nombre_base(forma) == nombre and not SUFIJO_MEGA.search(forma)), {})
    return _habilidad_base(nombre, base, datos)


def _validar_puntos(nombre, puntos):
    for stat, cantidad in puntos.items():
        if not 0 <= cantidad <= 32:
            raise ValueError(f"Puntos inválidos para {nombre}: {stat} tiene {cantidad}; debe estar entre 0 y 32.")
    total = sum(puntos.values())
    if total > 66:
        raise ValueError(f"Puntos inválidos para {nombre}: total {total}; el máximo es 66.")


def _spread(estadisticas, nombre):
    """Suma usos por orientación y escoge el spread más usado en la ganadora."""
    spreads = []
    porcentajes = {"fisica": 0, "especial": 0}
    for spread in _ordenados(estadisticas.get("spreads", {})):
        try:
            naturaleza, reparto = spread.split(":")
            puntos = [int(punto) for punto in reparto.split("/")]
        except (ValueError, AttributeError):
            continue
        if len(puntos) != 6:
            continue
        _validar_puntos(nombre, dict(zip(ESTADISTICAS, puntos)))
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


def set_probable(nombre, uso_smogon, datos, movimientos=None, variante=None):
    """Elige spread y movimientos compatibles con la orientación dominante.

    Smogon publica distribuciones separadas; esta aproximación evita combinar
    ataques físicos y especiales de orientaciones distintas. Si falta el
    catálogo de movimientos, no se filtra por categoría. Protect se omite
    siempre con objetos Choice. Si hay variantes, todo procede de la elegida
    (la más usada por defecto). Una Mega lleva su piedra y una habilidad legal
    de la base: la de la Mega si la comparte, o la más usada en la forma normal.
    """
    forma = seleccionar_variante(nombre, uso_smogon, variante)
    estadisticas = entrada_variante(nombre, uso_smogon, variante)
    if not estadisticas:
        return None
    if movimientos is None:
        movimientos = _cargar_movimientos()
    objetos = _objetos(estadisticas, datos, forma)
    orientacion, naturaleza, puntos = _spread(estadisticas, nombre)
    _validar_puntos(nombre, puntos)
    objeto = objetos[0] if objetos else None
    ataques = _movimientos_probables(estadisticas, orientacion, movimientos, objeto)
    return {"nombre": nombre, "habilidad": _habilidad_variante(nombre, forma, estadisticas, uso_smogon, datos),
            "objeto": objeto,
            "movimientos": ataques, "orientacion": orientacion,
            "naturaleza": naturaleza, "puntos": puntos}


def set_generico(nombre, datos, movimientos):
    """Construye un set sin objeto con ataques del learnset, priorizando STAB."""
    especie = datos[nombre]
    stats = especie["stats"]
    fisico = stats["attack"] >= stats["special-attack"]
    orientacion = "fisica" if fisico else "especial"
    categoria = "physical" if fisico else "special"
    puntos = dict.fromkeys(ESTADISTICAS, 0)
    puntos.update({"attack" if fisico else "special-attack": 32, "speed": 32, "hp": 2})
    _validar_puntos(nombre, puntos)
    learnset = {normalizar_id(movimiento) for movimiento in especie.get("movimientos", [])}
    tipos = {tipo.lower() for tipo in especie["tipos"]}
    ataques = [movimiento for movimiento in learnset
               if movimientos.get(movimiento, {}).get("categoria", "").lower() == categoria
               and movimientos[movimiento].get("potencia", 0) > 0]
    ataques.sort(key=lambda movimiento: (
        movimientos[movimiento].get("tipo", "").lower() not in tipos,
        -movimientos[movimiento]["potencia"], movimiento,
    ))
    elegidos = (["protect"] if "protect" in learnset else []) + ataques[:3]
    return {"nombre": nombre, "habilidad": _habilidad_base(nombre, {}, datos),
            "objeto": None, "movimientos": elegidos, "orientacion": orientacion,
            "naturaleza": "Adamant" if fisico else "Modest", "puntos": puntos,
            "generico": True}


def sets_equipo(equipo, uso_smogon, datos, movimientos=None, variantes=None):
    """Conserva todos los miembros y resuelve Item Clause según el uso."""
    if movimientos is None:
        movimientos = _cargar_movimientos()
    sets = []
    variantes = variantes or {}
    for nombre in equipo:
        entrada = set_probable(nombre, uso_smogon, datos, movimientos, variantes.get(nombre))
        if entrada is None:
            entrada = set_generico(nombre, datos, movimientos)
        sets.append(entrada)
    uso = {nombre: entrada_variante(nombre, uso_smogon, variantes.get(nombre)) or {}
           for nombre in equipo}
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
        nombre = entrada["nombre"]
        forma = seleccionar_variante(nombre, uso_smogon, variantes.get(nombre))
        alternativas = _objetos(uso[nombre], datos, forma) if forma else _ordenados(uso[nombre].get("objetos", {}))
        entrada["objeto"] = next((objeto for objeto in alternativas if objeto not in ocupados), None)
        if entrada["objeto"]:
            ocupados.add(entrada["objeto"])
        entrada["movimientos"] = _movimientos_probables(
            uso[entrada["nombre"]], entrada["orientacion"], movimientos, entrada["objeto"]
        )
    return sets
