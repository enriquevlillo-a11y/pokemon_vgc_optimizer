"""Lista de comprobación del meta basada en tipos y velocidades."""

import json

from config import ruta_pokemon_datos, ruta_movimientos
from importar_showdown import normalizar_id
from datos_uso import entrada_uso, entrada_variante, forma_variante, habilidades_de
from motor_tipos import calcular_defensas
from velocidad import velocidad, velocidades_reales


def amenazas_del_meta(uso_smogon, n=20, datos=None, variantes=None):
    """Las n especies con mayor uso y los tipos de la variante elegida.

    ``variantes`` es un diccionario especie -> forma; por defecto gana el uso.
    Sin variantes se conserva la Mega habitual del esquema antiguo.
    Los datos de especies se cargan desde config.py si no se proporcionan.
    """
    if datos is None:
        datos = json.loads(ruta_pokemon_datos().read_text(encoding="utf-8"))
    pokemon = (uso_smogon or {}).get("pokemon", uso_smogon or {})
    ordenadas = sorted(pokemon, key=lambda nombre: (-pokemon[nombre].get("uso", 0), nombre))
    resultado = []
    variantes = variantes or {}
    for nombre in ordenadas[:max(0, n)]:
        forma = forma_variante(nombre, uso_smogon, datos, variantes.get(nombre))
        resultado.append({
            "nombre": nombre,
            "uso": pokemon[nombre].get("uso", 0),
            "tipos": datos[forma]["tipos"],
            "forma": forma,
        })
    return resultado


def _estado(le_pegan, debiles):
    if not le_pegan:
        return "sin respuesta"
    return "en riesgo" if len(debiles) >= 3 else "cubierta"


def _defensas(nombre, forma, datos, uso_smogon, variante=None):
    defensas = calcular_defensas(datos[forma]["tipos"])
    if (entrada_uso(nombre, uso_smogon) or {}).get("variantes"):
        # Inmunidades de la forma elegida, con el mismo umbral de uso que los roles.
        inmunidades = {"levitate": "ground", "flashfire": "fire", "waterabsorb": "water",
                      "stormdrain": "water", "dryskin": "water", "voltabsorb": "electric",
                      "lightningrod": "electric", "motordrive": "electric", "sapsipper": "grass"}
        for habilidad in habilidades_de(nombre, datos, uso_smogon, variante):
            if habilidad in inmunidades:
                defensas[inmunidades[habilidad]] = 0
    return defensas


def _ataques(nombre, forma, datos, uso_smogon, movimientos, variante=None):
    estadisticas = entrada_variante(nombre, uso_smogon, variante)
    if estadisticas is None:
        return [(tipo, None) for tipo in datos[forma]["tipos"]]
    return [
        (movimiento.get("tipo", "").lower(), movimiento.get("nombre", identificador))
        for identificador, porcentaje in estadisticas.get("movimientos", {}).items()
        if porcentaje >= 20
        for movimiento in [movimientos.get(normalizar_id(identificador), {})]
        if movimiento.get("categoria", "").lower() not in ("", "status")
        and movimiento.get("potencia", 0) > 0
    ]


def revisar_equipo(equipo, datos, uso_smogon, n=20, movimientos=None, variantes=None):
    """Cobertura de ataques frecuentes, con fallback a tipos propios sin Smogon.

    Compara la velocidad máxima de cada miembro (32 puntos, naturaleza favorable,
    sin Scarf/Tailwind) con el spread más usado de la amenaza, o su máximo cuando
    falta. ``variantes`` permite elegir la forma por especie tanto para los
    miembros como para las amenazas. Sin variantes mantiene el cálculo antiguo.
    """
    if movimientos is None:
        ruta = ruta_movimientos()
        movimientos = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
    variantes = variantes or {}
    ataques, formas = {}, {}
    for miembro in equipo:
        tiene_variantes = (entrada_uso(miembro, uso_smogon) or {}).get("variantes")
        formas[miembro] = forma_variante(miembro, uso_smogon, datos, variantes.get(miembro)) if tiene_variantes else miembro
        ataques[miembro] = _ataques(miembro, formas[miembro], datos, uso_smogon, movimientos, variantes.get(miembro))
    defensas = {nombre: _defensas(nombre, formas[nombre], datos, uso_smogon, variantes.get(nombre)) for nombre in equipo}
    velocidades = {nombre: velocidad(formas[nombre], datos) for nombre in equipo}
    resultado = []
    for amenaza in amenazas_del_meta(uso_smogon, n, datos, variantes):
        nombre_amenaza = amenaza["nombre"]
        variante = variantes.get(nombre_amenaza)
        defensa = _defensas(nombre_amenaza, amenaza["forma"], datos, uso_smogon, variante)
        le_pegan, con = [], {}
        for miembro in equipo:
            efectivos = [movimiento for tipo, movimiento in ataques[miembro] if defensa.get(tipo, 1) > 1]
            if efectivos:
                le_pegan.append(miembro)
                con[miembro] = [movimiento for movimiento in efectivos if movimiento]
        forma = amenaza["forma"]
        if (entrada_uso(nombre_amenaza, uso_smogon) or {}).get("variantes"):
            tipos_ataque = [tipo for tipo, _ in _ataques(nombre_amenaza, forma, datos, uso_smogon, movimientos, variante)]
        else:
            tipos_ataque = amenaza["tipos"]
        debiles = [nombre for nombre in equipo if any(defensas[nombre].get(tipo, 1) > 1 for tipo in tipos_ataque)]
        real = velocidades_reales(nombre_amenaza, uso_smogon, datos, variante).get(forma)
        referencia = real if real is not None else velocidad(forma, datos)
        mas_rapidos = [nombre for nombre in equipo if velocidades[nombre] > referencia]
        resultado.append({
            **amenaza,
            "le_pegan": le_pegan,
            "con": con,
            "sin_respuesta": not le_pegan,
            "debiles": debiles,
            "mas_rapidos": mas_rapidos,
            "estado": _estado(le_pegan, debiles),
        })
    return resultado
